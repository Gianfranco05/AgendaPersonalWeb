"""Calculo de habitos pendientes, rachas y vista del dia (fuente unica).

El scheduler y `GET /today` usan EXACTAMENTE las mismas funciones: lo que la UI
dice que se va a avisar es lo que el scheduler evalua.

Gotcha: para un habito binario `Goal.is_completed` queda en true para siempre
despues del primer check-in de la historia. NO sirve para saber si el habito
esta hecho hoy: hay que mirar los `HabitRecord` del dia local.
"""

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.habitos_recordatorios import rules
from app.modules.habitos_recordatorios.models import (
    HabitReminderDispatch,
    HabitReminderSettings,
)
from app.modules.metas.models import Goal, HabitRecord
from app.modules.push.models import PushToken

HABIT_GOAL_TYPES = ("binary", "metric")


@dataclass(frozen=True)
class ReminderConfig:
    enabled: bool = True
    hour: int = rules.DEFAULT_HOUR
    minute: int = rules.DEFAULT_MINUTE
    daily_cap: int = rules.DEFAULT_DAILY_CAP
    streak_alerts: bool = True
    timezone_offset_minutes: Optional[int] = None

    @property
    def general_slot(self) -> int:
        return rules.slot_minutes(self.hour, self.minute)

    @property
    def time(self) -> str:
        return rules.format_hhmm(self.hour, self.minute)


def config_from_row(row: Optional[HabitReminderSettings]) -> ReminderConfig:
    """Sin fila: los avisos estan ENCENDIDOS con los defaults."""
    if row is None:
        return ReminderConfig()
    return ReminderConfig(
        enabled=bool(row.enabled),
        hour=row.hour,
        minute=row.minute,
        daily_cap=row.daily_cap,
        streak_alerts=bool(row.streak_alerts),
        timezone_offset_minutes=row.timezone_offset_minutes,
    )


async def get_settings_row(db: AsyncSession, user_id: str) -> Optional[HabitReminderSettings]:
    result = await db.execute(
        select(HabitReminderSettings).where(HabitReminderSettings.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_config(db: AsyncSession, user_id: str) -> ReminderConfig:
    return config_from_row(await get_settings_row(db, user_id))


async def has_push_devices(db: AsyncSession, user_id: str) -> bool:
    result = await db.execute(
        select(func.count()).select_from(PushToken).where(PushToken.user_id == user_id)
    )
    return (result.scalar() or 0) > 0


@dataclass(frozen=True)
class PendingHabit:
    id: str
    title: str
    icon: Optional[str]
    slot: int  # minutos del dia local en que se avisa (propia o general)

    @property
    def slot_label(self) -> str:
        return rules.format_slot(self.slot)


async def pending_habits(
    db: AsyncSession, user_id: str, local_date: date, general_slot: int
) -> list[PendingHabit]:
    """Habitos que faltan marcar en `local_date` (fecha LOCAL del usuario).

    Pendiente = binario/metrico, con aviso activo, dentro de su rango de fechas
    y con suma de registros del dia <= 0 (un metrico con cualquier valor > 0 ya
    cuenta como hecho). Los registros se filtran por habito Y por usuario.
    """
    day_totals = (
        select(HabitRecord.goal_id.label("goal_id"), func.sum(HabitRecord.value).label("total"))
        .where(HabitRecord.user_id == user_id, HabitRecord.record_date == local_date)
        .group_by(HabitRecord.goal_id)
        .subquery()
    )
    total = func.coalesce(day_totals.c.total, 0)
    stmt = (
        select(Goal.id, Goal.title, Goal.icon, Goal.reminder_hour, Goal.reminder_minute)
        .outerjoin(day_totals, day_totals.c.goal_id == Goal.id)
        .where(
            Goal.user_id == user_id,
            Goal.goal_type.in_(HABIT_GOAL_TYPES),
            Goal.reminder_enabled.is_(True),
            (Goal.start_date.is_(None)) | (Goal.start_date <= local_date),
            (Goal.end_date.is_(None)) | (Goal.end_date >= local_date),
            total <= 0,
        )
        .order_by(Goal.created_at, Goal.id)
    )
    habits = []
    for goal_id, title, icon, hour, minute in (await db.execute(stmt)).all():
        slot = general_slot if hour is None or minute is None else rules.slot_minutes(hour, minute)
        habits.append(PendingHabit(id=goal_id, title=title, icon=icon, slot=slot))
    return habits


async def streaks_until_yesterday(
    db: AsyncSession, user_id: str, goal_ids: list[str], local_date: date
) -> dict[str, int]:
    """Dias seguidos con total > 0 que terminan AYER (hoy todavia no cuenta: el
    habito esta pendiente). Hasta 365 dias hacia atras, en una sola consulta."""
    if not goal_ids:
        return {}
    since = local_date - timedelta(days=rules.STREAK_LOOKBACK_DAYS)
    stmt = (
        select(HabitRecord.goal_id, HabitRecord.record_date)
        .where(
            HabitRecord.user_id == user_id,
            HabitRecord.goal_id.in_(goal_ids),
            HabitRecord.record_date >= since,
            HabitRecord.record_date < local_date,
        )
        .group_by(HabitRecord.goal_id, HabitRecord.record_date)
        .having(func.sum(HabitRecord.value) > 0)
    )
    days: dict[str, set[date]] = {gid: set() for gid in goal_ids}
    for goal_id, record_date in (await db.execute(stmt)).all():
        days[goal_id].add(record_date)
    streaks: dict[str, int] = {}
    for goal_id, marked in days.items():
        count = 0
        cursor = local_date - timedelta(days=1)
        while cursor in marked:
            count += 1
            cursor -= timedelta(days=1)
        streaks[goal_id] = count
    return streaks


async def dispatches_for(
    db: AsyncSession, user_id: str, local_date: date
) -> list[HabitReminderDispatch]:
    result = await db.execute(
        select(HabitReminderDispatch).where(
            HabitReminderDispatch.user_id == user_id,
            HabitReminderDispatch.local_date == local_date,
        )
    )
    return list(result.scalars().all())


def encode_goal_ids(goal_ids: list[str]) -> str:
    return json.dumps(goal_ids)


# ── Vista del dia ───────────────────────────────────────────────────────────


@dataclass
class OverviewHabit:
    id: str
    title: str
    icon: Optional[str]
    streak: int


@dataclass
class OverviewSlot:
    time: str
    status: str
    habits: list[OverviewHabit] = field(default_factory=list)


@dataclass
class Overview:
    local_date: date
    enabled: bool
    pending_count: int
    slots: list[OverviewSlot]


async def today_overview(
    db: AsyncSession,
    user_id: str,
    tz_offset: Optional[int] = None,
    now_utc: Optional[datetime] = None,
) -> Overview:
    cfg = await get_config(db, user_id)
    offset = tz_offset if tz_offset is not None else cfg.timezone_offset_minutes
    local = rules.local_now(now_utc or datetime.now(timezone.utc), offset)
    local_date = local.date()
    minutes = rules.minutes_of_day(local)

    pending = await pending_habits(db, user_id, local_date, cfg.general_slot)
    streaks = await streaks_until_yesterday(db, user_id, [h.id for h in pending], local_date)
    recorded = {d.slot: d.status for d in await dispatches_for(db, user_id, local_date)}

    by_slot: dict[int, list[OverviewHabit]] = {}
    for habit in pending:
        by_slot.setdefault(habit.slot, []).append(
            OverviewHabit(habit.id, habit.title, habit.icon, streaks.get(habit.id, 0))
        )
    for label in recorded:
        by_slot.setdefault(rules.slot_minutes(*rules.parse_hhmm(label)), [])

    slots = []
    for slot in sorted(by_slot):
        label = rules.format_slot(slot)
        status = recorded.get(label) or rules.slot_state(slot, minutes)
        slots.append(OverviewSlot(time=label, status=status, habits=by_slot[slot]))
    return Overview(
        local_date=local_date,
        enabled=cfg.enabled,
        pending_count=len(pending),
        slots=slots,
    )

"""Avisos push de habitos sin marcar (via Expo).

A la hora elegida (20:00 locales por defecto, o la propia de cada habito) el
server revisa que habitos del usuario no tienen registro HOY (en su dia local)
y manda UNA push por hora con los que faltan. Si ya marco todo, no manda nada.

Los avisos estan ENCENDIDOS por defecto: un usuario con al menos un push token
y sin fila de configuracion se evalua con los defaults. Quien no tiene tokens no
se evalua (no hay a quien avisar).

Como en los avisos de vencimiento, hay una VENTANA (la hora, hasta 60 minutos
despues, sin pasar de la medianoche local): si el server estuvo caido a las
20:00 el aviso sale en el primer ciclo de la ventana; pasada la ventana, o con
otro dia local, ya no se manda (nada de avisos viejos).

Un ciclo por minuto y varios workers de gunicorn (cada uno con su scheduler)
requieren tres capas de dedup por (usuario, dia local, hora):

1. un set en memoria por proceso;
2. un claim `SET NX` en Redis compartido entre workers (se saltea sin Redis);
3. una fila UNICA en `habit_reminder_dispatches` insertada ANTES de mandar: solo
   manda el proceso cuyo INSERT salio bien. Cubre reinicios y despliegues sin
   Redis, y da el conteo para el tope diario.

Semantica at-most-once: la marca se escribe antes de mandar, asi que si Expo
falla el aviso se pierde (igual que recordatorios y vencimientos).
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_claim import claim_once, release_claim
from app.database import AsyncSessionLocal
from app.modules.habitos_recordatorios import rules, service
from app.modules.habitos_recordatorios.models import (
    HabitReminderDispatch,
    HabitReminderSettings,
)
from app.modules.metas.models import Goal
from app.modules.push.models import PushToken
from app.modules.push.service import PushService

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60
#: 36 h cubre el dia local completo en cualquier huso horario.
CLAIM_TTL_SECONDS = 129600
RETENTION_DAYS = 30

#: (user_id, fecha local, "HH:MM") ya procesados por este proceso.
_handled: set[tuple[str, date, str]] = set()
#: Ultimo dia UTC en que este proceso podo las filas viejas.
_last_prune: Optional[date] = None


@dataclass
class UserPlan:
    """Lo que el ciclo necesita saber de un usuario con habitos para avisar."""

    general_slot: int = rules.slot_minutes(rules.DEFAULT_HOUR, rules.DEFAULT_MINUTE)
    offset: Optional[int] = None
    daily_cap: int = rules.DEFAULT_DAILY_CAP
    streak_alerts: bool = True
    slots: set[int] = field(default_factory=set)


async def _candidates(db: AsyncSession) -> dict[str, UserPlan]:
    """Una consulta liviana: habitos con aviso de usuarios que tienen al menos un
    push token y cuya configuracion esta habilitada O NO EXISTE (encendido por
    defecto). Se agrupa en memoria por usuario -> horas a evaluar."""
    S = HabitReminderSettings
    has_token = select(PushToken.id).where(PushToken.user_id == Goal.user_id).exists()
    stmt = (
        select(
            Goal.user_id,
            Goal.reminder_hour,
            Goal.reminder_minute,
            S.hour,
            S.minute,
            S.timezone_offset_minutes,
            S.daily_cap,
            S.streak_alerts,
        )
        .select_from(Goal)
        .outerjoin(S, S.user_id == Goal.user_id)
        .where(
            Goal.goal_type.in_(service.HABIT_GOAL_TYPES),
            Goal.reminder_enabled.is_(True),
            or_(S.id.is_(None), S.enabled.is_(True)),
            has_token,
        )
    )
    plans: dict[str, UserPlan] = {}
    for user_id, g_hour, g_min, s_hour, s_min, offset, cap, streaks in (await db.execute(stmt)).all():
        plan = plans.get(user_id)
        if plan is None:
            plan = plans[user_id] = UserPlan(
                general_slot=rules.slot_minutes(
                    rules.DEFAULT_HOUR if s_hour is None else s_hour,
                    rules.DEFAULT_MINUTE if s_min is None else s_min,
                ),
                offset=offset,
                daily_cap=rules.DEFAULT_DAILY_CAP if cap is None else cap,
                streak_alerts=True if streaks is None else bool(streaks),
            )
        if g_hour is None or g_min is None:
            plan.slots.add(plan.general_slot)
        else:
            plan.slots.add(rules.slot_minutes(g_hour, g_min))
    return plans


async def _insert_dispatches(
    db: AsyncSession,
    user_id: str,
    local_date: date,
    entries: list[tuple[str, str, list[str]]],
) -> None:
    """Inserta las marcas del grupo en UNA transaccion. La restriccion unica
    (usuario, dia, hora) hace que, de varios procesos, solo uno lo logre."""
    for slot, status, goal_ids in entries:
        db.add(
            HabitReminderDispatch(
                user_id=user_id,
                local_date=local_date,
                slot=slot,
                status=status,
                goal_ids=service.encode_goal_ids(goal_ids) if goal_ids else None,
            )
        )
    await db.commit()


async def _evaluate(user_id: str, plan: UserPlan, local_date: date, claimed: list[int]) -> set[str]:
    """Calcula, marca y (si corresponde) manda. Devuelve los slots cuya marca
    persistente YA existia (los hizo otro proceso o un ciclo previo): esos no se
    reintentan. Si falla algo antes de marcar, la excepcion sube y el llamador
    libera los claims para reintentar en el ciclo siguiente."""
    labels = {slot: rules.format_slot(slot) for slot in claimed}
    async with AsyncSessionLocal() as db:
        pending = [
            h
            for h in await service.pending_habits(db, user_id, local_date, plan.general_slot)
            if h.slot in labels
        ]
        by_slot: dict[int, list[service.PendingHabit]] = {}
        for habit in pending:
            by_slot.setdefault(habit.slot, []).append(habit)
        with_pending = sorted(by_slot)

        entries: list[tuple[str, str, list[str]]] = []
        for slot in claimed:
            if slot not in by_slot:
                entries.append((labels[slot], "nothing", []))

        push_title = push_body = None
        goal_ids_sent: list[str] = []
        if with_pending:
            primary = with_pending[0]
            union = [h for h in pending]  # orden de creacion de los habitos
            sent_today = (
                await db.execute(
                    select(func.count())
                    .select_from(HabitReminderDispatch)
                    .where(
                        HabitReminderDispatch.user_id == user_id,
                        HabitReminderDispatch.local_date == local_date,
                        HabitReminderDispatch.status == "sent",
                    )
                )
            ).scalar() or 0
            if sent_today >= plan.daily_cap:
                primary_status = "capped"
            elif not await PushService(db).tokens_for_user(user_id):
                primary_status = "no_devices"
            else:
                primary_status = "sent"
            other_status = "merged" if primary_status == "sent" else primary_status
            goal_ids_sent = [h.id for h in union]
            entries.append((labels[primary], primary_status, goal_ids_sent))
            for slot in with_pending[1:]:
                entries.append((labels[slot], other_status, [h.id for h in by_slot[slot]]))
            if primary_status == "sent":
                streaks = await service.streaks_until_yesterday(
                    db, user_id, goal_ids_sent, local_date
                )
                push_title, push_body = rules.build_message(
                    [(h.id, h.title, h.icon) for h in union], streaks, plan.streak_alerts
                )
        entries.sort(key=lambda e: e[0])

        try:
            await _insert_dispatches(db, user_id, local_date, entries)
        except IntegrityError:
            # Postgres aborta la transaccion tras el conflicto: rollback antes
            # de volver a usar la sesion.
            await db.rollback()
            existing = (
                await db.execute(
                    select(HabitReminderDispatch.slot).where(
                        HabitReminderDispatch.user_id == user_id,
                        HabitReminderDispatch.local_date == local_date,
                    )
                )
            ).scalars().all()
            return set(existing) | {"__conflict__"}
        except Exception:
            await db.rollback()
            raise

    if push_title is not None:
        try:
            async with AsyncSessionLocal() as push_db:
                await PushService(push_db).send_to_user(
                    user_id,
                    push_title,
                    push_body,
                    data={
                        "type": "habit_reminder",
                        "local_date": local_date.isoformat(),
                        "goal_ids": goal_ids_sent,
                    },
                )
        except Exception:
            # Expo caido (o lo que sea): la marca ya esta escrita, no se reintenta.
            logger.exception("Fallo el aviso de habitos del usuario %s", user_id)
    return set()


async def _process_user(user_id: str, plan: UserPlan, now_utc: datetime) -> None:
    local = rules.local_now(now_utc, plan.offset)
    local_date = local.date()
    minutes = rules.minutes_of_day(local)

    due = sorted(
        slot
        for slot in plan.slots
        if rules.window_contains(slot, minutes)
        and (user_id, local_date, rules.format_slot(slot)) not in _handled
    )
    if not due:
        return

    claimed: list[int] = []
    for slot in due:
        label = rules.format_slot(slot)
        _handled.add((user_id, local_date, label))
        if await claim_once(f"habit-reminder:{user_id}:{local_date.isoformat()}:{label}", CLAIM_TTL_SECONDS):
            claimed.append(slot)
    if not claimed:
        return

    async def give_back(slots: list[int]) -> None:
        for slot in slots:
            label = rules.format_slot(slot)
            _handled.discard((user_id, local_date, label))
            await release_claim(f"habit-reminder:{user_id}:{local_date.isoformat()}:{label}")

    try:
        existing = await _evaluate(user_id, plan, local_date, claimed)
    except Exception:
        # La marca persistente no se escribio (DB caida un instante): se
        # reintenta en el proximo ciclo dentro de la ventana.
        await give_back(claimed)
        raise
    if existing:
        # Conflicto: otro proceso (o un ciclo previo antes de un reinicio) ya
        # marco. Los slots con marca quedan hechos; los demas se reintentan.
        await give_back([s for s in claimed if rules.format_slot(s) not in existing])


async def _prune(now_utc: datetime) -> None:
    global _last_prune
    today = now_utc.date()
    if _last_prune == today:
        return
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(HabitReminderDispatch).where(
                    HabitReminderDispatch.local_date < today - timedelta(days=RETENTION_DAYS)
                )
            )
            await db.commit()
        _last_prune = today
    except Exception:
        logger.exception("No se pudo podar habit_reminder_dispatches")


async def _tick(now_utc: Optional[datetime] = None) -> None:
    now_utc = now_utc or datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        plans = await _candidates(db)
    for user_id, plan in plans.items():
        try:
            await _process_user(user_id, plan, now_utc)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Un usuario roto (o Expo caido) no frena a los demas ni al loop.
            logger.exception("Fallo el aviso de habitos del usuario %s", user_id)

    await _prune(now_utc)
    cutoff = now_utc.date() - timedelta(days=2)
    for stale in [k for k in _handled if k[1] < cutoff]:
        _handled.discard(stale)


async def run_habit_reminder_scheduler() -> None:
    """Loop de fondo arrancado desde el lifespan, un ciclo por minuto alineado al
    inicio del minuto. Un ciclo fallido se loguea y el loop sigue."""
    while True:
        try:
            await _tick()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Fallo un ciclo del scheduler de avisos de habitos")
        now = datetime.now(timezone.utc)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS - now.second - now.microsecond / 1e6 + 1)

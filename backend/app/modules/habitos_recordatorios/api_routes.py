from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.modules.auth.models import User
from app.modules.habitos_recordatorios import rules, service
from app.modules.habitos_recordatorios.models import HabitReminderSettings
from app.modules.habitos_recordatorios.schemas import (
    HabitReminderSettingsOut,
    HabitReminderSettingsUpdate,
    OverviewHabitOut,
    OverviewSlotOut,
    TodayOverviewOut,
)

# El modulo de habitos es base (sin `require_module`): solo autenticacion.
router = APIRouter(prefix="/habit-reminders", tags=["habits"])


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def _settings_out(db: AsyncSession, user_id: str) -> HabitReminderSettingsOut:
    cfg = await service.get_config(db, user_id)
    return HabitReminderSettingsOut(
        enabled=cfg.enabled,
        time=cfg.time,
        daily_cap=cfg.daily_cap,
        streak_alerts=cfg.streak_alerts,
        timezone_offset_minutes=cfg.timezone_offset_minutes,
        has_push_devices=await service.has_push_devices(db, user_id),
    )


async def _get_or_create_row(db: AsyncSession, user_id: str) -> HabitReminderSettings:
    """La fila se crea en el primer PUT. Dos PUT simultaneos del mismo usuario
    nuevo (reintento de la cola offline) chocan con el UNIQUE de user_id: el que
    pierde se queda con la fila del ganador."""
    row = await service.get_settings_row(db, user_id)
    if row is not None:
        return row
    db.add(HabitReminderSettings(user_id=user_id))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
    return (
        await db.execute(
            select(HabitReminderSettings).where(HabitReminderSettings.user_id == user_id)
        )
    ).scalar_one()


@router.get("/settings", response_model=HabitReminderSettingsOut)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Un GET nunca crea filas: sin configuracion se devuelven los defaults
    # (avisos encendidos).
    return await _settings_out(db, current_user.id)


@router.put("/settings", response_model=HabitReminderSettingsOut)
async def update_settings(
    data: HabitReminderSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_or_create_row(db, current_user.id)
    changes = data.model_dump(exclude_unset=True)
    # Las columnas no admiten null: un null explicito se ignora. El offset si
    # puede borrarse (null = Argentina).
    for key in ("enabled", "time", "daily_cap", "streak_alerts"):
        if changes.get(key) is None:
            changes.pop(key, None)
    if "time" in changes:
        row.hour, row.minute = rules.parse_hhmm(changes.pop("time"))
    for key, value in changes.items():
        setattr(row, key, value)
    await db.commit()
    return await _settings_out(db, current_user.id)


@router.get("/today", response_model=TodayOverviewOut)
async def today(
    tz_offset_minutes: Optional[int] = Query(
        None, ge=-840, le=840, description="Minutos al este de UTC (Buenos Aires = -180)"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    overview = await service.today_overview(
        db, current_user.id, tz_offset_minutes, now_utc=utc_now()
    )
    return TodayOverviewOut(
        local_date=overview.local_date,
        enabled=overview.enabled,
        pending_count=overview.pending_count,
        slots=[
            OverviewSlotOut(
                time=slot.time,
                status=slot.status,
                habits=[
                    OverviewHabitOut(id=h.id, title=h.title, icon=h.icon, streak=h.streak)
                    for h in slot.habits
                ],
            )
            for slot in overview.slots
        ],
    )

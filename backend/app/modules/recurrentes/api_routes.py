from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.modules.auth.models import User
from app.modules.recurrentes import rules
from app.modules.recurrentes.schemas import (
    ConfirmIn,
    OccurrenceOut,
    PreviewIn,
    PreviewOut,
    RecurringCreate,
    RecurringDetailOut,
    RecurringOut,
    RecurringUpdate,
    TzBody,
    UpcomingOut,
)
from app.modules.recurrentes.service import RecurringService

# Parte de Finanzas (plantilla base): sin `require_module`, solo autenticacion.
# Las rutas estaticas van antes de `/{id}`: si no, "upcoming" se leeria como un id.
router = APIRouter(prefix="/finance/recurring", tags=["finance"])

TzOffset = Query(
    rules.DEFAULT_TZ_OFFSET_MINUTES,
    ge=-840,
    le=840,
    description="Minutos al este de UTC (Buenos Aires = -180)",
)


def _today(offset: Optional[int]):
    return rules.local_today(rules.utc_now(), offset)


async def _own(service: RecurringService, recurrence_id: str, user: User):
    rec = await service.get(recurrence_id, user.id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Recurrencia no encontrada")
    return rec


@router.get("", response_model=list[RecurringOut])
async def list_recurring(
    status_filter: Literal["active", "paused", "all"] = Query("all", alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await RecurringService(db).list_out(current_user.id, status_filter)


@router.post("", response_model=RecurringOut, status_code=status.HTTP_201_CREATED)
async def create_recurring(
    data: RecurringCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecurringService(db)
    rec = await service.create(current_user.id, data)
    return await service.out(rec)


@router.post("/preview", response_model=PreviewOut)
async def preview_recurring(
    data: PreviewIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return RecurringService(db).preview(data, _today(data.tz_offset_minutes))


@router.get("/upcoming", response_model=UpcomingOut)
async def upcoming_recurring(
    days: int = Query(30, ge=1, le=90),
    tz_offset_minutes: int = TzOffset,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await RecurringService(db).upcoming(current_user.id, _today(tz_offset_minutes), days)


@router.get("/occurrences", response_model=list[OccurrenceOut])
async def list_occurrences(
    status_filter: Literal["pending", "all"] = Query("pending", alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await RecurringService(db).pending_out(current_user.id, status_filter == "pending")


@router.post("/occurrences/{occurrence_id}/confirm", response_model=OccurrenceOut)
async def confirm_occurrence(
    occurrence_id: str,
    data: ConfirmIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await RecurringService(db).confirm(current_user.id, occurrence_id, data)


@router.post("/occurrences/{occurrence_id}/skip", response_model=OccurrenceOut)
async def skip_occurrence(
    occurrence_id: str,
    data: Optional[TzBody] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = data.timezone_offset_minutes if data else None
    return await RecurringService(db).skip(current_user.id, occurrence_id, offset)


@router.get("/{recurrence_id}", response_model=RecurringDetailOut)
async def get_recurring(
    recurrence_id: str,
    tz_offset_minutes: int = TzOffset,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecurringService(db)
    rec = await _own(service, recurrence_id, current_user)
    return await service.detail(rec, _today(tz_offset_minutes))


@router.put("/{recurrence_id}", response_model=RecurringOut)
async def update_recurring(
    recurrence_id: str,
    data: RecurringUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecurringService(db)
    rec = await _own(service, recurrence_id, current_user)
    rec = await service.update(rec, data)
    return await service.out(rec)


@router.delete("/{recurrence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring(
    recurrence_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecurringService(db)
    rec = await _own(service, recurrence_id, current_user)
    await service.delete(rec)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{recurrence_id}/pause", response_model=RecurringOut)
async def pause_recurring(
    recurrence_id: str,
    data: Optional[TzBody] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecurringService(db)
    rec = await _own(service, recurrence_id, current_user)
    rec = await service.pause(rec, data.timezone_offset_minutes if data else None)
    return await service.out(rec)


@router.post("/{recurrence_id}/resume", response_model=RecurringOut)
async def resume_recurring(
    recurrence_id: str,
    data: Optional[TzBody] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecurringService(db)
    rec = await _own(service, recurrence_id, current_user)
    rec = await service.resume(rec, data.timezone_offset_minutes if data else None)
    return await service.out(rec)

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.eventos.service import EventosService
from app.modules.eventos.schemas import EventCreate, EventUpdate, EventResponse

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventResponse])
async def list_events(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = EventosService(db)
    events = await service.get_events(
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
    )
    return events


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = EventosService(db)
    event = await service.create_event(current_user.id, data)
    return event


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    data: EventUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = EventosService(db)
    event = await service.get_event(event_id, current_user.id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    updated = await service.update_event(event, data)
    return updated


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = EventosService(db)
    event = await service.get_event(event_id, current_user.id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    await service.delete_event(event)

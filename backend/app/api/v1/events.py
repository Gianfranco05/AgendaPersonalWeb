from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.eventos.service import EventosService
from app.modules.eventos.schemas import EventCreate, EventUpdate, EventResponse, to_wall_clock

router = APIRouter(prefix="/events", tags=["events"])


def _escape_ics(value: str) -> str:
    if not value:
        return ""
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


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


@router.get("/export/ics")
async def export_events_ics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exporta los eventos del usuario como .ics. Portado de la ruta HTML
    legacy `/eventos/exportar/ics`."""
    service = EventosService(db)
    events = await service.get_events(user_id=current_user.id)
    events = sorted(events, key=lambda e: e.start_datetime)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Can_cen//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for event in events:
        # Hora de pared: sin "Z", el calendario la toma como hora local
        # flotante (con "Z" la correria a UTC).
        start_str = to_wall_clock(event.start_datetime).strftime("%Y%m%dT%H%M%S")
        end_str = (
            to_wall_clock(event.end_datetime).strftime("%Y%m%dT%H%M%S")
            if event.end_datetime
            else start_str
        )

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{event.id}@cancen")
        lines.append(f"SUMMARY:{_escape_ics(event.title)}")
        lines.append(f"DTSTART:{start_str}")
        lines.append(f"DTEND:{end_str}")
        if event.description:
            lines.append(f"DESCRIPTION:{_escape_ics(event.description)}")
        if event.location:
            lines.append(f"LOCATION:{_escape_ics(event.location)}")
        lines.append(
            f"DTSTAMP:{event.created_at.strftime('%Y%m%dT%H%M%SZ')}"
            if event.created_at
            else f"DTSTAMP:{start_str}"
        )
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    ics_content = "\r\n".join(lines) + "\r\n"

    return StreamingResponse(
        iter([ics_content.encode("utf-8")]),
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=eventos.ics"},
    )

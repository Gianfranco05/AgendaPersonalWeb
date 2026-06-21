from app.core.security import get_user_id_from_request

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.eventos.models import Event

router = APIRouter(prefix="/eventos", tags=["eventos-export"])


def _escape_ics(value: str) -> str:
    """Escape special characters for ICS text values."""
    if not value:
        return ""
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


@router.get("/exportar/ics")
async def exportar_eventos_ics(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Event)
        .where(Event.user_id == user_id)
        .order_by(Event.start_datetime.asc())
    )
    events = result.scalars().all()

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Vida Personal//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for event in events:
        start_str = event.start_datetime.strftime("%Y%m%dT%H%M%SZ")
        if event.end_datetime:
            end_str = event.end_datetime.strftime("%Y%m%dT%H%M%SZ")
        else:
            end_str = start_str

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{event.id}@vidapersonal")
        lines.append(f"SUMMARY:{_escape_ics(event.title)}")
        lines.append(f"DTSTART:{start_str}")
        lines.append(f"DTEND:{end_str}")
        if event.description:
            lines.append(f"DESCRIPTION:{_escape_ics(event.description)}")
        if event.location:
            lines.append(f"LOCATION:{_escape_ics(event.location)}")
        lines.append(f"DTSTAMP:{event.created_at.strftime('%Y%m%dT%H%M%SZ') if event.created_at else start_str}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")

    ics_content = "\r\n".join(lines) + "\r\n"

    return StreamingResponse(
        iter([ics_content.encode("utf-8")]),
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=eventos.ics"},
    )

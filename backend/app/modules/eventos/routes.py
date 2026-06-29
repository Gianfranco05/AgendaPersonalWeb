import logging

from datetime import datetime, date, timedelta, timezone
from uuid import uuid4
import json

from app.core.security import get_user_id_from_request
from app.core.templates import templates

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.eventos.models import Event
from app.modules.anotaciones.models import Note

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eventos", tags=["eventos"])


@router.get("/")
async def calendario(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Event).where(Event.user_id == get_user_id_from_request(request))
    )
    events = result.scalars().all()

    notes_result = await db.execute(
        select(Note).where(
            Note.user_id == get_user_id_from_request(request),
            Note.is_archived == False,
            Note.event_date != None,
        )
    )
    notes = notes_result.scalars().all()

    events_list = []
    for e in events:
        events_list.append(
            {
                "id": e.id,
                "title": e.title,
                "start": e.start_datetime.isoformat() if e.start_datetime else None,
                "end": e.end_datetime.isoformat() if e.end_datetime else None,
                "color": e.color,
                "allDay": e.is_all_day,
                "description": e.description,
                "location": e.location,
                "type": "event",
            }
        )

    for n in notes:
        events_list.append(
            {
                "id": f"note_{n.id}",
                "title": f"📝 {n.title}",
                "start": n.event_date.isoformat() if n.event_date else None,
                "color": n.color,
                "allDay": True,
                "description": n.content,
                "type": "note",
                "note_id": n.id,
            }
        )

    today = date.today().isoformat()
    events_json = json.dumps(events_list)
    return templates.TemplateResponse(request, "eventos/calendario.html", {"active_page": "calendario", "events_list": events_list, "events_json": events_json, "today": today})


@router.get("/nuevo")
async def nuevo_evento(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    note_id = request.query_params.get("from_note")
    note = None
    if note_id:
        result = await db.execute(
            select(Note).where(
                Note.id == note_id, Note.user_id == get_user_id_from_request(request)
            )
        )
        note = result.scalar_one_or_none()

    if note and note.event_date:
        start_date_val = note.event_date.strftime("%Y-%m-%d")
    else:
        start_date_val = date.today().isoformat()
    start_time_val = "09:00"

    return templates.TemplateResponse(request, "eventos/formulario.html", {"active_page": "calendario", "event": None, "note": note, "start_date_val": start_date_val, "start_time_val": start_time_val})


@router.post("/nuevo")
async def crear_evento(
    request: Request,
    db: AsyncSession = Depends(get_db),
    title: str = Form(...),
    description: str = Form(""),
    start_date: str = Form(...),
    start_time: str = Form("09:00"),
    is_all_day: str = Form("false"),
    color: str = Form("#3b82f6"),
    location: str = Form(""),
    from_note_id: str = Form(""),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    try:
        start_dt = datetime.strptime(
            f"{start_date} {start_time}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=timezone.utc)

        event = Event(
            id=str(uuid4()),
            user_id=get_user_id_from_request(request),
            title=title,
            description=description or None,
            start_datetime=start_dt,
            is_all_day=is_all_day.lower() == "true",
            color=color,
            location=location or None,
        )
        db.add(event)

        if from_note_id:
            note_result = await db.execute(
                select(Note).where(
                    Note.id == from_note_id, Note.user_id == get_user_id_from_request(request)
                )
            )
            note = note_result.scalar_one_or_none()
            if note:
                note.event_date = None

        await db.commit()
    except Exception as e:
        logger.exception("Error creating event")
        await db.rollback()

    return RedirectResponse(url="/finanzas/", status_code=303)


@router.get("/editar/{event_id}")
async def editar_evento_form(
    request: Request, event_id: str, db: AsyncSession = Depends(get_db)
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Event).where(
            Event.id == event_id, Event.user_id == get_user_id_from_request(request)
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        return RedirectResponse(url="/finanzas/", status_code=303)

    if event.start_datetime:
        start_date_val = event.start_datetime.strftime("%Y-%m-%d")
        start_time_val = event.start_datetime.strftime("%H:%M")
    else:
        start_date_val = date.today().isoformat()
        start_time_val = "09:00"

    return templates.TemplateResponse(request, "eventos/formulario.html", {"active_page": "calendario", "event": event, "note": None, "start_date_val": start_date_val, "start_time_val": start_time_val})


@router.post("/editar/{event_id}")
async def editar_evento(
    request: Request,
    event_id: str,
    db: AsyncSession = Depends(get_db),
    title: str = Form(...),
    description: str = Form(""),
    start_date: str = Form(...),
    start_time: str = Form("09:00"),
    is_all_day: str = Form("false"),
    color: str = Form("#3b82f6"),
    location: str = Form(""),
    action: str = Form("save"),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Event).where(
            Event.id == event_id, Event.user_id == get_user_id_from_request(request)
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        return RedirectResponse(url="/finanzas/", status_code=303)

    if action == "delete":
        await db.delete(event)
    else:
        event.title = title
        event.description = description or None
        event.start_datetime = datetime.strptime(
            f"{start_date} {start_time}", "%Y-%m-%d %H:%M"
        )
        event.is_all_day = is_all_day.lower() == "true"
        event.color = color
        event.location = location or None

    await db.commit()
    return RedirectResponse(url="/finanzas/", status_code=303)

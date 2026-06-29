import logging

from uuid import uuid4
from datetime import datetime, date

from app.core.security import get_user_id_from_request
from app.core.templates import templates

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.anotaciones.models import Note, Tag, note_tags

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/anotaciones", tags=["anotaciones"])


@router.get("/")
async def lista_notas(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Note)
        .options(selectinload(Note.tags))
        .where(Note.user_id == get_user_id_from_request(request))
        .where(Note.is_archived == False)
        .order_by(Note.is_pinned.desc(), Note.updated_at.desc())
    )
    notes = result.scalars().all()

    tags_result = await db.execute(
        select(Tag).where(Tag.user_id == get_user_id_from_request(request)).order_by(Tag.name)
    )
    tags = tags_result.scalars().all()

    return templates.TemplateResponse(request, "anotaciones/lista.html", {"active_page": "notas", "notes": notes, "tags": tags})


@router.get("/nueva")
async def nueva_nota(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    tags_result = await db.execute(
        select(Tag).where(Tag.user_id == get_user_id_from_request(request)).order_by(Tag.name)
    )
    tags = tags_result.scalars().all()

    return templates.TemplateResponse(request, "anotaciones/formulario.html", {"active_page": "notas", "note": None, "tags": tags})


@router.post("/nueva")
async def crear_nota(
    request: Request,
    db: AsyncSession = Depends(get_db),
    title: str = Form(...),
    content: str = Form(""),
    color: str = Form("#ffffff"),
    event_date: str = Form(""),
    tags: str = Form(""),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    try:
        event_date_val = None
        if event_date:
            event_date_val = datetime.strptime(event_date, "%Y-%m-%d").date()

        note = Note(
            id=str(uuid4()),
            user_id=get_user_id_from_request(request),
            title=title,
            content=content,
            color=color,
            event_date=event_date_val,
        )
        db.add(note)
        await db.flush()

        if tags:
            tag_ids = [t.strip() for t in tags.split(",") if t.strip()]
            for tag_id in tag_ids:
                tag_result = await db.execute(
                    select(Tag).where(
                        Tag.id == tag_id, Tag.user_id == get_user_id_from_request(request)
                    )
                )
                tag = tag_result.scalar_one_or_none()
                if tag:
                    await db.execute(
                        note_tags.insert().values(note_id=note.id, tag_id=tag.id)
                    )

        await db.commit()
    except Exception:
        logger.exception("Error creating note")
        await db.rollback()

    return RedirectResponse(url="/finanzas/", status_code=303)


@router.get("/editar/{note_id}")
async def editar_nota_form(
    request: Request, note_id: str, db: AsyncSession = Depends(get_db)
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Note)
        .options(selectinload(Note.tags))
        .where(
            Note.id == note_id, Note.user_id == get_user_id_from_request(request)
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        return RedirectResponse(url="/anotaciones/", status_code=303)

    tags_result = await db.execute(
        select(Tag).where(Tag.user_id == get_user_id_from_request(request)).order_by(Tag.name)
    )
    tags = tags_result.scalars().all()

    return templates.TemplateResponse(request, "anotaciones/formulario.html", {"active_page": "notas", "note": note, "tags": tags})


@router.post("/editar/{note_id}")
async def editar_nota(
    request: Request,
    note_id: str,
    db: AsyncSession = Depends(get_db),
    title: str = Form(...),
    content: str = Form(""),
    color: str = Form("#ffffff"),
    event_date: str = Form(""),
    tags: str = Form(""),
    action: str = Form("save"),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Note)
        .options(selectinload(Note.tags))
        .where(
            Note.id == note_id, Note.user_id == get_user_id_from_request(request)
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        return RedirectResponse(url="/anotaciones/", status_code=303)

    if action == "delete":
        note.is_archived = True
    else:
        note.title = title
        note.content = content
        note.color = color
        if event_date:
            try:
                note.event_date = datetime.strptime(event_date, "%Y-%m-%d").date()
            except ValueError:
                note.event_date = None
        else:
            note.event_date = None

        note.tags.clear()
        if tags:
            tag_ids = [t.strip() for t in tags.split(",") if t.strip()]
            for tag_id in tag_ids:
                tag_result = await db.execute(
                    select(Tag).where(
                        Tag.id == tag_id, Tag.user_id == get_user_id_from_request(request)
                    )
                )
                tag = tag_result.scalar_one_or_none()
                if tag:
                    note.tags.append(tag)

    await db.commit()
    return RedirectResponse(url="/finanzas/", status_code=303)


@router.get("/etiquetas")
async def etiquetas(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    tags_result = await db.execute(
        select(Tag).where(Tag.user_id == get_user_id_from_request(request)).order_by(Tag.name)
    )
    tags = tags_result.scalars().all()

    return templates.TemplateResponse(request, "anotaciones/etiquetas.html", {"active_page": "notas", "tags": tags})


@router.post("/etiquetas")
async def crear_etiqueta(
    request: Request,
    db: AsyncSession = Depends(get_db),
    name: str = Form(...),
    color: str = Form("#6366f1"),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    tag = Tag(
        id=str(uuid4()),
        user_id=get_user_id_from_request(request),
        name=name,
        color=color,
    )
    db.add(tag)
    await db.commit()

    return RedirectResponse(url="/anotaciones/etiquetas", status_code=303)


@router.post("/etiquetas/eliminar/{tag_id}")
async def eliminar_etiqueta(
    request: Request,
    tag_id: str,
    db: AsyncSession = Depends(get_db),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.user_id == get_user_id_from_request(request))
    )
    tag = result.scalar_one_or_none()
    if tag:
        await db.delete(tag)
        await db.commit()

    return RedirectResponse(url="/anotaciones/etiquetas", status_code=303)


@router.get("/api/tags")
async def api_tags(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Tag).where(Tag.user_id == get_user_id_from_request(request)).order_by(Tag.name)
    )
    tags = result.scalars().all()

    return {"tags": [{"id": t.id, "name": t.name, "color": t.color} for t in tags]}

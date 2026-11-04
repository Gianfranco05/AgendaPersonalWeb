import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.anotaciones.models import Note
from app.modules.anotaciones.service import AnotacionesService
from app.modules.anotaciones.schemas import (
    NoteCreate,
    NoteUpdate,
    NoteResponse,
    TagResponse,
)

router = APIRouter(prefix="/notes", tags=["notes"])


class NoteDetailResponse(NoteResponse):
    tags: list[TagResponse] = []


@router.get("", response_model=list[NoteDetailResponse])
async def list_notes(
    search: Optional[str] = None,
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnotacionesService(db)
    notes = await service.get_notes(
        user_id=current_user.id,
        include_archived=include_archived,
        search=search,
    )
    return notes


@router.post("", response_model=NoteDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    data: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnotacionesService(db)
    note = await service.create_note(
        user_id=current_user.id,
        title=data.title,
        content=data.content,
        color=data.color,
        is_pinned=data.is_pinned,
    )

    if data.tag_names:
        result = await db.execute(
            select(Note)
            .where(and_(Note.id == note.id, Note.user_id == current_user.id))
            .options(selectinload(Note.tags))
        )
        note = result.scalar_one()

        for tag_name in data.tag_names:
            tag = await service.create_tag(current_user.id, tag_name)
            await service.add_tag_to_note(note, tag)

    result = await db.execute(
        select(Note)
        .where(and_(Note.id == note.id, Note.user_id == current_user.id))
        .options(selectinload(Note.tags))
    )
    note = result.scalar_one()
    return note


@router.put("/{note_id}", response_model=NoteDetailResponse)
async def update_note(
    note_id: str,
    data: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnotacionesService(db)
    note = await service.get_note(note_id, current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="Nota no encontrada")

    await service.update_note(note, data)

    if data.tag_names is not None:
        # update_note hace refresh: se vuelve a traer con los tags cargados
        # antes de reasignar la coleccion.
        note = await service.get_note(note_id, current_user.id)
        await service.set_note_tags(note, current_user.id, data.tag_names)

    result = await db.execute(
        select(Note)
        .where(and_(Note.id == note_id, Note.user_id == current_user.id))
        .options(selectinload(Note.tags))
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnotacionesService(db)
    note = await service.get_note(note_id, current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="Nota no encontrada")

    await service.delete_note(note)


@router.get("/tags", response_model=list[TagResponse])
async def list_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnotacionesService(db)
    tags = await service.get_tags(current_user.id)
    return tags


@router.get("/export/json")
async def export_notes_json(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exporta las notas no archivadas del usuario como .json. Portado de la
    ruta HTML legacy `/anotaciones/exportar/json`."""
    result = await db.execute(
        select(Note)
        .where(Note.user_id == current_user.id)
        .where(Note.is_archived == False)
        .order_by(Note.updated_at.desc())
        .options(selectinload(Note.tags))
    )
    notes = result.scalars().all()

    data = [
        {
            "id": note.id,
            "title": note.title,
            "content": note.content,
            "color": note.color,
            "tags": [t.name for t in note.tags],
            "event_date": note.event_date.isoformat() if note.event_date else None,
            "created_at": note.created_at.isoformat() if note.created_at else None,
            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        }
        for note in notes
    ]

    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    return StreamingResponse(
        iter([json_bytes]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=notas.json"},
    )

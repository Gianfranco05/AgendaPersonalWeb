from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
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


class NoteCreateRequest(BaseModel):
    title: str
    content: str
    color: str = "#ffffff"
    tag_names: list[str] = []


class NoteUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    color: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None


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
    data: NoteCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnotacionesService(db)
    note = await service.create_note(
        user_id=current_user.id,
        title=data.title,
        content=data.content,
        color=data.color,
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
    data: NoteUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AnotacionesService(db)
    note = await service.get_note(note_id, current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="Nota no encontrada")

    note_update = NoteUpdate(**data.model_dump(exclude_unset=True))
    updated = await service.update_note(note, note_update)
    return updated


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

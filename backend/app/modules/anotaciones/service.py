from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.anotaciones.models import Note, Tag
from app.modules.anotaciones.repository import NoteRepository, TagRepository
from app.modules.anotaciones.schemas import NoteCreate, NoteUpdate


class AnotacionesService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.note_repo = NoteRepository(db)
        self.tag_repo = TagRepository(db)

    async def create_note(
        self,
        user_id: UUID,
        title: str,
        content: str,
        color: str = "#ffffff",
        is_pinned: bool = False,
    ) -> Note:
        note = Note(
            user_id=user_id,
            title=title,
            content=content,
            color=color,
            is_pinned=is_pinned,
        )
        return await self.note_repo.create(note)

    async def get_notes(
        self,
        user_id: UUID,
        include_archived: bool = False,
        search: Optional[str] = None,
    ) -> Sequence[Note]:
        return await self.note_repo.get_all(user_id, include_archived, search)

    async def get_note(self, note_id: UUID, user_id: UUID) -> Optional[Note]:
        return await self.note_repo.get_by_id(note_id, user_id)

    async def update_note(self, note: Note, data: NoteUpdate) -> Note:
        if data.title is not None:
            note.title = data.title
        if data.content is not None:
            note.content = data.content
        if data.color is not None:
            note.color = data.color
        if data.is_pinned is not None:
            note.is_pinned = data.is_pinned
        if data.is_archived is not None:
            note.is_archived = data.is_archived

        return await self.note_repo.update(note)

    async def delete_note(self, note: Note) -> None:
        await self.note_repo.delete(note)

    async def toggle_pin(self, note: Note) -> Note:
        note.is_pinned = not note.is_pinned
        return await self.note_repo.update(note)

    async def toggle_archive(self, note: Note) -> Note:
        note.is_archived = not note.is_archived
        return await self.note_repo.update(note)

    async def get_tags(self, user_id: UUID) -> Sequence[Tag]:
        return await self.tag_repo.get_all(user_id)

    async def create_tag(self, user_id: UUID, name: str, color: str = "#6366f1") -> Tag:
        existing = await self.tag_repo.get_by_name(name, user_id)
        if existing:
            return existing

        tag = Tag(
            user_id=user_id,
            name=name,
            color=color,
        )
        return await self.tag_repo.create(tag)

    async def set_note_tags(self, note: Note, user_id: UUID, tag_names: list[str]) -> None:
        """Reemplaza los tags de la nota por exactamente `tag_names`.

        `note` tiene que venir con `tags` ya cargado (selectinload): reasignar
        una coleccion sin cargar dispara un lazy-load sincrono que en sesion
        async explota con MissingGreenlet.
        """
        # dict.fromkeys: saca vacios y duplicados conservando el orden.
        names = dict.fromkeys(n.strip() for n in tag_names if n.strip())
        note.tags = [await self.create_tag(user_id, name) for name in names]
        await self.db.commit()

    async def add_tag_to_note(self, note: Note, tag: Tag) -> None:
        if tag not in note.tags:
            note.tags.append(tag)
            await self.db.commit()

    async def remove_tag_from_note(self, note: Note, tag: Tag) -> None:
        if tag in note.tags:
            note.tags.remove(tag)
            await self.db.commit()

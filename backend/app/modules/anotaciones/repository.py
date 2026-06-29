from typing import Sequence, Optional

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.anotaciones.models import Note, Tag


class NoteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        user_id: str,
        include_archived: bool = False,
        search: Optional[str] = None,
    ) -> Sequence[Note]:
        query = select(Note).where(Note.user_id == user_id)

        if not include_archived:
            query = query.where(Note.is_archived == False)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Note.title.ilike(search_term),
                    Note.content.ilike(search_term),
                )
            )

        query = query.order_by(Note.is_pinned.desc(), Note.updated_at.desc())
        query = query.options(selectinload(Note.tags))

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_id(self, note_id: str, user_id: str) -> Optional[Note]:
        result = await self.db.execute(
            select(Note)
            .where(and_(Note.id == note_id, Note.user_id == user_id))
            .options(selectinload(Note.tags))
        )
        return result.scalar_one_or_none()

    async def create(self, note: Note) -> Note:
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def update(self, note: Note) -> Note:
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def delete(self, note: Note) -> None:
        await self.db.delete(note)
        await self.db.commit()


class TagRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, user_id: str) -> Sequence[Tag]:
        result = await self.db.execute(
            select(Tag).where(Tag.user_id == user_id).order_by(Tag.name)
        )
        return result.scalars().all()

    async def get_by_name(self, name: str, user_id: str) -> Optional[Tag]:
        result = await self.db.execute(
            select(Tag).where(and_(Tag.name == name, Tag.user_id == user_id))
        )
        return result.scalar_one_or_none()

    async def create(self, tag: Tag) -> Tag:
        self.db.add(tag)
        await self.db.commit()
        await self.db.refresh(tag)
        return tag

    async def delete(self, tag: Tag) -> None:
        await self.db.delete(tag)
        await self.db.commit()

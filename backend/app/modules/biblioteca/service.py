from typing import Optional

from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud_service import apply_changes, get_by_id_or_404
from app.modules.biblioteca.models import BOOK_STATUSES, Book, BookStatus


class LibraryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _validate_status(self, status: Optional[str]) -> None:
        if status is not None and status not in BOOK_STATUSES:
            raise HTTPException(status_code=422, detail="Estado de libro inválido")

    async def list_books(self, user_id: str, status: Optional[str] = None) -> list[Book]:
        self._validate_status(status)
        query = select(Book).where(Book.user_id == user_id)
        if status:
            query = query.where(Book.status == status)
        result = await self.db.execute(query.order_by(Book.updated_at.desc()))
        return list(result.scalars().all())

    async def _get_book(self, user_id: str, book_id: str) -> Book:
        return await get_by_id_or_404(
            self.db, Book, book_id, user_id, not_found_detail="Libro no encontrado"
        )

    async def create_book(
        self,
        user_id: str,
        title: str,
        author: Optional[str] = None,
        status: Optional[str] = None,
        rating: Optional[float] = None,
        pages: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Book:
        self._validate_status(status)
        book = Book(
            user_id=user_id,
            title=title,
            author=author or None,
            status=status or BookStatus.PENDIENTE,
            rating=rating,
            pages=pages,
            notes=notes or None,
        )
        self.db.add(book)
        await self.db.commit()
        await self.db.refresh(book)
        return book

    async def update_book(self, user_id: str, book_id: str, changes: dict) -> Book:
        book = await self._get_book(user_id, book_id)
        self._validate_status(changes.get("status"))
        apply_changes(book, changes)
        await self.db.commit()
        await self.db.refresh(book)
        return book

    async def delete_book(self, user_id: str, book_id: str) -> None:
        book = await self._get_book(user_id, book_id)
        await self.db.delete(book)
        await self.db.commit()

    async def summary(self, user_id: str) -> dict:
        result = await self.db.execute(
            select(
                func.count(Book.id),
                func.sum(case((Book.status == BookStatus.PENDIENTE, 1), else_=0)),
                func.sum(case((Book.status == BookStatus.LEYENDO, 1), else_=0)),
                func.sum(case((Book.status == BookStatus.LEIDO, 1), else_=0)),
                func.avg(case((Book.status == BookStatus.LEIDO, Book.rating), else_=None)),
            ).where(Book.user_id == user_id)
        )
        total, pendientes, leyendo, leidos, average_rating = result.one()

        return {
            "total": total or 0,
            "pendientes": pendientes or 0,
            "leyendo": leyendo or 0,
            "leidos": leidos or 0,
            "average_rating": round(average_rating, 1) if average_rating is not None else None,
        }

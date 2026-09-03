from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
        result = await self.db.execute(
            select(Book).where(Book.id == book_id, Book.user_id == user_id)
        )
        book = result.scalar_one_or_none()
        if book is None:
            raise HTTPException(status_code=404, detail="Libro no encontrado")
        return book

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
        for field, value in changes.items():
            if value is not None:
                setattr(book, field, value)
        await self.db.commit()
        await self.db.refresh(book)
        return book

    async def delete_book(self, user_id: str, book_id: str) -> None:
        book = await self._get_book(user_id, book_id)
        await self.db.delete(book)
        await self.db.commit()

    async def summary(self, user_id: str) -> dict:
        books = await self.list_books(user_id)
        leidos = [b for b in books if b.status == BookStatus.LEIDO]
        rated = [b.rating for b in leidos if b.rating is not None]

        return {
            "total": len(books),
            "pendientes": sum(1 for b in books if b.status == BookStatus.PENDIENTE),
            "leyendo": sum(1 for b in books if b.status == BookStatus.LEYENDO),
            "leidos": len(leidos),
            "average_rating": round(sum(rated) / len(rated), 1) if rated else None,
        }

from uuid import uuid4
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Float, Integer, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class BookStatus:
    PENDIENTE = "pendiente"
    LEYENDO = "leyendo"
    LEIDO = "leido"


BOOK_STATUSES = frozenset({BookStatus.PENDIENTE, BookStatus.LEYENDO, BookStatus.LEIDO})


class Book(Base):
    """Un libro leido, en curso o pendiente en la biblioteca del usuario.

    Rating en estrellas (0 a 5, con medios puntos) y no en la escala 0-10 de
    Estudio a proposito: son dominios distintos (una nota académica no es lo
    mismo que un puntaje de gusto personal) y 0-5 es la convencion que ya
    espera cualquiera que puntuo un libro antes.
    """

    __tablename__ = "books"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    author: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=BookStatus.PENDIENTE, index=True)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    started_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    finished_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

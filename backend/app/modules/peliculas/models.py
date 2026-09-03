from uuid import uuid4
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class MediaType:
    PELICULA = "pelicula"
    SERIE = "serie"


MEDIA_TYPES = frozenset({MediaType.PELICULA, MediaType.SERIE})


class MediaStatus:
    PENDIENTE = "pendiente"
    VIENDO = "viendo"
    VISTO = "visto"


MEDIA_STATUSES = frozenset({MediaStatus.PENDIENTE, MediaStatus.VIENDO, MediaStatus.VISTO})


class MediaItem(Base):
    """Una pelicula o serie vista, en curso o pendiente."""

    __tablename__ = "media_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    media_type: Mapped[str] = mapped_column(String(20), default=MediaType.PELICULA)
    status: Mapped[str] = mapped_column(String(20), default=MediaStatus.PENDIENTE, index=True)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

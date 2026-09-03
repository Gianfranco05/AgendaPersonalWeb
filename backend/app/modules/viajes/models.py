from uuid import uuid4
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Float, Boolean, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class TripStatus:
    PLANEADO = "planeado"
    EN_CURSO = "en_curso"
    COMPLETADO = "completado"


TRIP_STATUSES = frozenset({TripStatus.PLANEADO, TripStatus.EN_CURSO, TripStatus.COMPLETADO})


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    destination: Mapped[str] = mapped_column(String(160))
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=TripStatus.PLANEADO, index=True)
    budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PackingItem(Base):
    """Item del checklist de equipaje de un viaje. Sin relacion con Task
    (el modulo base): es una lista descartable por viaje, no una tarea con
    fecha limite y prioridad."""

    __tablename__ = "packing_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    trip_id: Mapped[str] = mapped_column(String(36), ForeignKey("trips.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    packed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

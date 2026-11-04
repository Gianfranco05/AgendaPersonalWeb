from uuid import uuid4
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Float, Integer, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class RecordType:
    COMBUSTIBLE = "combustible"
    REVISION = "revision"
    ITV = "itv"
    GASTO = "gasto"


RECORD_TYPES = frozenset(
    {RecordType.COMBUSTIBLE, RecordType.REVISION, RecordType.ITV, RecordType.GASTO}
)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    brand: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    plate: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MaintenanceRecord(Base):
    """Un evento del historial de un vehiculo: carga de combustible, revision
    tecnica, ITV o un gasto mecanico suelto."""

    __tablename__ = "maintenance_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), index=True)
    record_type: Mapped[str] = mapped_column(String(20), index=True)
    record_date: Mapped[date] = mapped_column(Date, index=True)
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    odometer_km: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

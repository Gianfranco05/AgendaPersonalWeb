from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, field_serializer, field_validator

# Convencion de fecha y hora de un evento: es "hora de pared", la que el usuario
# escribio, sin zona horaria. Web y mobile mandan y esperan de vuelta un
# datetime SIN offset ("2026-10-07T10:00:00") y lo muestran tal cual. La
# columna es timestamptz, asi que se guarda como esa misma hora de pared en UTC
# (nunca se interpreta segun la zona del servidor) y se devuelve sin offset.
# Sin esto, en Postgres la respuesta salia con "Z" y el cliente la corria
# 3 horas (Argentina, UTC-3); SQLite lo escondia porque descarta la zona.


def to_storage(value: datetime) -> datetime:
    """Hora de pared -> valor para la columna: naive se toma como UTC, uno con
    offset se pasa a UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def to_wall_clock(value: datetime) -> datetime:
    """Valor de la columna -> hora de pared naive (lo que ven los clientes)."""
    return to_storage(value).replace(tzinfo=None)


class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    is_all_day: bool = False
    color: str = "#3b82f6"
    location: Optional[str] = None
    recurrence_rule: Optional[str] = None
    reminder_minutes: Optional[int] = None

    @field_validator("start_datetime", "end_datetime")
    @classmethod
    def _normalize_datetime(cls, v):
        return to_storage(v) if v is not None else v


class EventCreate(EventBase):
    @field_validator("end_datetime")
    @classmethod
    def end_after_start(cls, v, info):
        # to_storage tambien aca: el orden entre este validator y el de la
        # base no esta garantizado, y comparar naive con aware revienta.
        if v and "start_datetime" in info.data and to_storage(v) < to_storage(
            info.data["start_datetime"]
        ):
            raise ValueError("La fecha de fin debe ser posterior a la fecha de inicio")
        return v


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    is_all_day: Optional[bool] = None
    color: Optional[str] = None
    location: Optional[str] = None
    recurrence_rule: Optional[str] = None
    reminder_minutes: Optional[int] = None

    @field_validator("start_datetime", "end_datetime")
    @classmethod
    def _normalize_datetime(cls, v):
        return to_storage(v) if v is not None else v


class EventResponse(EventBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("start_datetime", "end_datetime")
    def _serialize_wall_clock(self, v: Optional[datetime]):
        return to_wall_clock(v).isoformat() if v is not None else None

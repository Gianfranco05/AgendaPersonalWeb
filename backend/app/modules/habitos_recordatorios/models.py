from datetime import date, datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class HabitReminderSettings(Base):
    """Configuracion de los avisos de habitos sin marcar (una fila por usuario).

    Los avisos estan ENCENDIDOS por defecto: un usuario sin fila se trata como
    habilitado con estos mismos defaults (ver `service.DEFAULTS`). La fila se
    crea recien en el primer PUT.
    """

    __tablename__ = "habit_reminder_settings"
    __table_args__ = (
        CheckConstraint("hour >= 0 AND hour <= 23", name="ck_habit_reminder_hour"),
        CheckConstraint("minute >= 0 AND minute <= 59", name="ck_habit_reminder_minute"),
        CheckConstraint("daily_cap >= 1 AND daily_cap <= 5", name="ck_habit_reminder_cap"),
        CheckConstraint(
            "timezone_offset_minutes IS NULL OR "
            "(timezone_offset_minutes >= -840 AND timezone_offset_minutes <= 840)",
            name="ck_habit_reminder_tz",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True, index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    hour: Mapped[int] = mapped_column(Integer, default=20, server_default="20")
    minute: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    daily_cap: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    streak_alerts: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    timezone_offset_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class HabitReminderDispatch(Base):
    """Marca persistente de que se evaluo un (usuario, dia local, hora).

    La restriccion unica es la que garantiza el "una sola vez" entre workers y
    reinicios; ademas sirve de contador para el tope diario.
    """

    __tablename__ = "habit_reminder_dispatches"
    __table_args__ = (
        UniqueConstraint("user_id", "local_date", "slot", name="uq_habit_reminder_dispatch"),
        Index("ix_habit_reminder_dispatch_user_date", "user_id", "local_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    local_date: Mapped[date] = mapped_column(Date)
    slot: Mapped[str] = mapped_column(String(5))
    # sent | merged | nothing | capped | no_devices
    status: Mapped[str] = mapped_column(String(12))
    goal_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

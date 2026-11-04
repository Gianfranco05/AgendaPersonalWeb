from uuid import uuid4
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    String,
    Text,
    Boolean,
    Integer,
    Float,
    ForeignKey,
    Date,
    DateTime,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint(
            "(reminder_hour IS NULL AND reminder_minute IS NULL) OR "
            "(reminder_hour IS NOT NULL AND reminder_minute IS NOT NULL AND "
            "reminder_hour >= 0 AND reminder_hour <= 23 AND "
            "reminder_minute >= 0 AND reminder_minute <= 59)",
            name="ck_goals_reminder_time",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    goal_type: Mapped[str] = mapped_column(String(20), default="binary")
    target_value: Mapped[float] = mapped_column(Float, nullable=True)
    current_value: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(50), nullable=True)
    color: Mapped[str] = mapped_column(String(7), default="#7C3AED")
    icon: Mapped[str] = mapped_column(String(50), default="fa-bullseye")
    start_date: Mapped[datetime] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime] = mapped_column(Date, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    # Aviso "no marcaste este habito hoy" (solo binary/metric). Sin hora propia
    # (ambas null) usa la hora general de habit_reminder_settings.
    reminder_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )
    reminder_hour: Mapped[int] = mapped_column(Integer, nullable=True)
    reminder_minute: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class HabitRecord(Base):
    __tablename__ = "habit_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    goal_id: Mapped[str] = mapped_column(String(36), ForeignKey("goals.id"))
    record_date: Mapped[datetime] = mapped_column(Date)
    value: Mapped[float] = mapped_column(Float, default=1)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

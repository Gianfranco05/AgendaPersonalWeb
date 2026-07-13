from uuid import uuid4
from datetime import datetime

from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    ForeignKey,
    Date,
    DateTime,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    session_date: Mapped[datetime] = mapped_column(Date)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    exercises: Mapped[list["Exercise"]] = relationship(
        "Exercise",
        back_populates="session",
        order_by="Exercise.order",
        cascade="all, delete-orphan",
    )


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workout_sessions.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    sets: Mapped[int] = mapped_column(Integer, nullable=True)
    reps: Mapped[int] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped["WorkoutSession"] = relationship(
        "WorkoutSession", back_populates="exercises"
    )

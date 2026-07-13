from uuid import uuid4
from datetime import datetime

from sqlalchemy import (
    String,
    Text,
    Float,
    ForeignKey,
    Date,
    DateTime,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    meal_date: Mapped[datetime] = mapped_column(Date, index=True)
    meal_type: Mapped[str] = mapped_column(String(20), default="breakfast")
    name: Mapped[str] = mapped_column(String(255))
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    calories: Mapped[float] = mapped_column(Float, nullable=True)
    protein_g: Mapped[float] = mapped_column(Float, nullable=True)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=True)
    fat_g: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

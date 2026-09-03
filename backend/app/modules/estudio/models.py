from uuid import uuid4
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Float, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class SubjectStatus:
    CURSANDO = "cursando"
    APROBADA = "aprobada"
    PENDIENTE = "pendiente"


SUBJECT_STATUSES = frozenset(
    {SubjectStatus.CURSANDO, SubjectStatus.APROBADA, SubjectStatus.PENDIENTE}
)


class Subject(Base):
    """Una materia de la carrera."""

    __tablename__ = "subjects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    professor: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    color: Mapped[str] = mapped_column(String(9), default="#6366F1")
    status: Mapped[str] = mapped_column(String(20), default=SubjectStatus.CURSANDO)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Exam(Base):
    """Un examen o entrega de una materia.

    La nota es Float y no Numeric a proposito: no es plata, no necesita
    aritmetica exacta, y Numeric vuelve como string en Postgres y como float en
    SQLite — una diferencia que el cliente tendria que absorber sin ganar nada.
    """

    __tablename__ = "exams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    subject_id: Mapped[str] = mapped_column(String(36), ForeignKey("subjects.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    exam_date: Mapped[date] = mapped_column(Date, index=True)
    grade: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

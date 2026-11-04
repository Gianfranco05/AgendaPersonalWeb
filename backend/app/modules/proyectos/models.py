from uuid import uuid4
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class ProjectStatus:
    ACTIVO = "activo"
    PAUSADO = "pausado"
    COMPLETADO = "completado"


PROJECT_STATUSES = frozenset(
    {ProjectStatus.ACTIVO, ProjectStatus.PAUSADO, ProjectStatus.COMPLETADO}
)


class TaskStatus:
    """Las 3 columnas del tablero Kanban."""

    PENDIENTE = "pendiente"
    EN_PROGRESO = "en_progreso"
    HECHO = "hecho"


TASK_STATUSES = frozenset({TaskStatus.PENDIENTE, TaskStatus.EN_PROGRESO, TaskStatus.HECHO})


class Project(Base):
    """Un proyecto con su propio tablero. Distinto del modulo base de Tareas:
    ese es la lista personal del dia a dia, esto es un tablero por proyecto
    con sus propias columnas."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ProjectStatus.ACTIVO, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ProjectTask(Base):
    __tablename__ = "project_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default=TaskStatus.PENDIENTE, index=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

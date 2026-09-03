from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.proyectos.models import (
    PROJECT_STATUSES,
    TASK_STATUSES,
    Project,
    ProjectStatus,
    ProjectTask,
    TaskStatus,
)


class ProjectsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _validate_project_status(self, status: Optional[str]) -> None:
        if status is not None and status not in PROJECT_STATUSES:
            raise HTTPException(status_code=422, detail="Estado de proyecto inválido")

    def _validate_task_status(self, status: Optional[str]) -> None:
        if status is not None and status not in TASK_STATUSES:
            raise HTTPException(status_code=422, detail="Estado de tarea inválido")

    # ── Proyectos ────────────────────────────────────────────────────────────

    async def list_projects(self, user_id: str) -> list[Project]:
        result = await self.db.execute(
            select(Project).where(Project.user_id == user_id).order_by(Project.updated_at.desc())
        )
        return list(result.scalars().all())

    async def _get_project(self, user_id: str, project_id: str) -> Project:
        result = await self.db.execute(
            select(Project).where(Project.id == project_id, Project.user_id == user_id)
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        return project

    async def create_project(
        self, user_id: str, name: str, description: Optional[str] = None, status: Optional[str] = None
    ) -> Project:
        self._validate_project_status(status)
        project = Project(
            user_id=user_id,
            name=name,
            description=description or None,
            status=status or ProjectStatus.ACTIVO,
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def update_project(self, user_id: str, project_id: str, changes: dict) -> Project:
        project = await self._get_project(user_id, project_id)
        self._validate_project_status(changes.get("status"))
        for field, value in changes.items():
            if value is not None:
                setattr(project, field, value)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete_project(self, user_id: str, project_id: str) -> None:
        project = await self._get_project(user_id, project_id)
        # Las tareas se borran explicitamente: no hay ON DELETE CASCADE y
        # SQLite ni siquiera aplica las foreign keys.
        await self.db.execute(delete(ProjectTask).where(ProjectTask.project_id == project.id))
        await self.db.delete(project)
        await self.db.commit()

    # ── Tareas del tablero ───────────────────────────────────────────────────

    async def list_tasks(self, user_id: str, project_id: Optional[str] = None) -> list[ProjectTask]:
        if project_id:
            await self._get_project(user_id, project_id)  # valida ownership
        query = select(ProjectTask).where(ProjectTask.user_id == user_id)
        if project_id:
            query = query.where(ProjectTask.project_id == project_id)
        result = await self.db.execute(query.order_by(ProjectTask.created_at))
        return list(result.scalars().all())

    async def _get_task(self, user_id: str, task_id: str) -> ProjectTask:
        result = await self.db.execute(
            select(ProjectTask).where(ProjectTask.id == task_id, ProjectTask.user_id == user_id)
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise HTTPException(status_code=404, detail="Tarea no encontrada")
        return task

    async def create_task(
        self,
        user_id: str,
        project_id: str,
        title: str,
        status: Optional[str] = None,
        due_date=None,
        notes: Optional[str] = None,
    ) -> ProjectTask:
        await self._get_project(user_id, project_id)  # valida que el proyecto sea del usuario
        self._validate_task_status(status)
        task = ProjectTask(
            user_id=user_id,
            project_id=project_id,
            title=title,
            status=status or TaskStatus.PENDIENTE,
            due_date=due_date,
            notes=notes or None,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def update_task(self, user_id: str, task_id: str, changes: dict) -> ProjectTask:
        task = await self._get_task(user_id, task_id)
        self._validate_task_status(changes.get("status"))
        for field, value in changes.items():
            if value is not None:
                setattr(task, field, value)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete_task(self, user_id: str, task_id: str) -> None:
        task = await self._get_task(user_id, task_id)
        await self.db.delete(task)
        await self.db.commit()

    # ── Resumen ──────────────────────────────────────────────────────────────

    async def summary(self, user_id: str) -> dict:
        projects = await self.list_projects(user_id)
        tasks = await self.list_tasks(user_id)

        return {
            "projects_total": len(projects),
            "projects_active": sum(1 for p in projects if p.status == ProjectStatus.ACTIVO),
            "tasks_pending": sum(1 for t in tasks if t.status == TaskStatus.PENDIENTE),
            "tasks_in_progress": sum(1 for t in tasks if t.status == TaskStatus.EN_PROGRESO),
            "tasks_done": sum(1 for t in tasks if t.status == TaskStatus.HECHO),
        }

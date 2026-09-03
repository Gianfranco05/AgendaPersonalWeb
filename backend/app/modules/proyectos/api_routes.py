from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.entitlements import require_module
from app.database import get_db
from app.modules.auth.models import User
from app.modules.proyectos.service import ProjectsService

# Plantilla de pago: sin la compra, el server no deja tocar estos endpoints.
router = APIRouter(
    prefix="/projects", tags=["projects"], dependencies=[Depends(require_module("projects"))]
)


class ProjectOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str

    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[str] = None


class ProjectTaskOut(BaseModel):
    id: str
    project_id: str
    title: str
    status: str
    due_date: Optional[date] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class ProjectTaskCreate(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=200)
    status: Optional[str] = None
    due_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class ProjectTaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    status: Optional[str] = None
    due_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class ProjectsSummaryOut(BaseModel):
    projects_total: int
    projects_active: int
    tasks_pending: int
    tasks_in_progress: int
    tasks_done: int


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ProjectsService(db).list_projects(str(current_user.id))


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ProjectsService(db).create_project(
        str(current_user.id), body.name, body.description, body.status
    )


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ProjectsService(db).update_project(
        str(current_user.id), project_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ProjectsService(db).delete_project(str(current_user.id), project_id)


@router.get("/tasks", response_model=list[ProjectTaskOut])
async def list_tasks(
    project_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ProjectsService(db).list_tasks(str(current_user.id), project_id)


@router.post("/tasks", response_model=ProjectTaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: ProjectTaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ProjectsService(db).create_task(
        str(current_user.id), body.project_id, body.title, body.status, body.due_date, body.notes
    )


@router.patch("/tasks/{task_id}", response_model=ProjectTaskOut)
async def update_task(
    task_id: str,
    body: ProjectTaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ProjectsService(db).update_task(
        str(current_user.id), task_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ProjectsService(db).delete_task(str(current_user.id), task_id)


@router.get("/summary", response_model=ProjectsSummaryOut)
async def get_projects_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ProjectsService(db).summary(str(current_user.id))

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.tareas.service import TasksService
from app.modules.tareas.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskMove,
    TaskResponse,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    area: Optional[str] = None,
    status_: Optional[str] = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TasksService(db)
    return await service.list_tasks(current_user.id, area=area, status=status_)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TasksService(db)
    return await service.create_task(current_user.id, data)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TasksService(db)
    task = await service.get_task(current_user.id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return await service.update_task(task, data)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TasksService(db)
    task = await service.get_task(current_user.id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    await service.delete_task(task)


@router.post("/{task_id}/move", response_model=TaskResponse)
async def move_task(
    task_id: str,
    data: TaskMove,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TasksService(db)
    task = await service.get_task(current_user.id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return await service.move_task(current_user.id, task, data.status, data.order)

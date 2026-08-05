from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tareas.models import Task
from app.modules.tareas.repository import TaskRepository
from app.modules.tareas.schemas import TaskCreate, TaskUpdate


class TasksService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TaskRepository(db)

    async def create_task(self, user_id: str, data: TaskCreate) -> Task:
        existing = await self.repo.get_by_status(user_id, data.status)
        order = len(existing)
        task = Task(
            user_id=user_id,
            title=data.title,
            description=data.description,
            area=data.area,
            priority=data.priority,
            due_date=data.due_date,
            status=data.status,
            order=order,
        )
        return await self.repo.create(task)

    async def list_tasks(
        self, user_id: str, area: Optional[str] = None, status: Optional[str] = None
    ) -> Sequence[Task]:
        return await self.repo.get_all(user_id, area, status)

    async def get_task(self, user_id: str, task_id: str) -> Optional[Task]:
        return await self.repo.get_by_id(task_id, user_id)

    async def update_task(self, task: Task, data: TaskUpdate) -> Task:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(task, key, value)
        return await self.repo.update(task)

    async def delete_task(self, task: Task) -> None:
        await self.repo.delete(task)

    async def move_task(
        self, user_id: str, task: Task, new_status: str, new_order: int
    ) -> Task:
        task.status = new_status
        column = list(await self.repo.get_by_status(user_id, new_status, exclude_id=task.id))
        new_order = max(0, min(new_order, len(column)))
        column.insert(new_order, task)
        for index, item in enumerate(column):
            item.order = index
        await self.repo.commit()
        await self.db.refresh(task)
        return task

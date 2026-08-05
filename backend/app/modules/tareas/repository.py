from typing import Optional, Sequence

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tareas.models import Task


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, task: Task) -> Task:
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_by_id(self, task_id: str, user_id: str) -> Optional[Task]:
        result = await self.db.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        user_id: str,
        area: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Sequence[Task]:
        query = select(Task).where(Task.user_id == user_id)
        if area:
            query = query.where(Task.area == area)
        if status:
            query = query.where(Task.status == status)
        query = query.order_by(Task.status.asc(), Task.order.asc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_status(
        self, user_id: str, status: str, exclude_id: Optional[str] = None
    ) -> Sequence[Task]:
        query = select(Task).where(
            and_(Task.user_id == user_id, Task.status == status)
        )
        if exclude_id:
            query = query.where(Task.id != exclude_id)
        query = query.order_by(Task.order.asc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update(self, task: Task) -> Task:
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete(self, task: Task) -> None:
        await self.db.delete(task)
        await self.db.commit()

    async def commit(self) -> None:
        await self.db.commit()

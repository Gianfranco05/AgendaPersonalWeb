from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.metas.models import Goal, HabitRecord


class GoalRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, goal: Goal) -> Goal:
        self.db.add(goal)
        await self.db.commit()
        await self.db.refresh(goal)
        return goal

    async def get_by_id(self, goal_id: str, user_id: str) -> Optional[Goal]:
        result = await self.db.execute(
            select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_active(self, user_id: str) -> list[Goal]:
        result = await self.db.execute(
            select(Goal)
            .where(Goal.user_id == user_id, Goal.is_completed == False)
            .order_by(Goal.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_completed(self, user_id: str) -> list[Goal]:
        result = await self.db.execute(
            select(Goal)
            .where(Goal.user_id == user_id, Goal.is_completed == True)
            .order_by(Goal.updated_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, goal: Goal) -> Goal:
        await self.db.commit()
        await self.db.refresh(goal)
        return goal

    async def delete(self, goal: Goal) -> None:
        await self.db.execute(
            delete(HabitRecord).where(HabitRecord.goal_id == goal.id)
        )
        await self.db.delete(goal)
        await self.db.commit()

    async def add_checkin(self, record: HabitRecord) -> HabitRecord:
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def get_recent_records(
        self, goal_id: str, days: int = 7
    ) -> list[HabitRecord]:
        result = await self.db.execute(
            select(HabitRecord)
            .where(HabitRecord.goal_id == goal_id)
            .where(HabitRecord.record_date >= date.today() - timedelta(days=days))
            .order_by(HabitRecord.record_date.desc())
        )
        return list(result.scalars().all())

    async def get_today_record(
        self, goal_id: str, today: date
    ) -> Optional[HabitRecord]:
        result = await self.db.execute(
            select(HabitRecord)
            .where(HabitRecord.goal_id == goal_id)
            .where(HabitRecord.record_date == today)
        )
        return result.scalar_one_or_none()

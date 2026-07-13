from datetime import date
from typing import Optional

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.fitness.models import WorkoutSession, Exercise


class FitnessRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, session: WorkoutSession) -> WorkoutSession:
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return await self.get_by_id(session.id, session.user_id)

    async def get_by_id(
        self, session_id: str, user_id: str
    ) -> Optional[WorkoutSession]:
        result = await self.db.execute(
            select(WorkoutSession)
            .options(selectinload(WorkoutSession.exercises))
            .where(WorkoutSession.id == session_id, WorkoutSession.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> list[WorkoutSession]:
        result = await self.db.execute(
            select(WorkoutSession)
            .options(selectinload(WorkoutSession.exercises))
            .where(WorkoutSession.user_id == user_id)
            .order_by(WorkoutSession.session_date.desc())
        )
        return list(result.scalars().all())

    async def update(self, session: WorkoutSession) -> WorkoutSession:
        await self.db.commit()
        return await self.get_by_id(session.id, session.user_id)

    async def delete(self, session: WorkoutSession) -> None:
        await self.db.execute(
            delete(Exercise).where(Exercise.session_id == session.id)
        )
        await self.db.delete(session)
        await self.db.commit()

    async def count_sessions_since(self, user_id: str, since: date) -> int:
        result = await self.db.execute(
            select(func.count(WorkoutSession.id)).where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.session_date >= since,
            )
        )
        return result.scalar_one() or 0

    async def count_total_exercises(self, user_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Exercise.id))
            .join(WorkoutSession, Exercise.session_id == WorkoutSession.id)
            .where(WorkoutSession.user_id == user_id)
        )
        return result.scalar_one() or 0

    async def get_last_session_date(self, user_id: str) -> Optional[date]:
        result = await self.db.execute(
            select(func.max(WorkoutSession.session_date)).where(
                WorkoutSession.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

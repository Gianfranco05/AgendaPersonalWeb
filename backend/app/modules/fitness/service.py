from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.fitness.models import WorkoutSession, Exercise
from app.modules.fitness.repository import FitnessRepository
from app.modules.fitness.schemas import (
    WorkoutSessionCreate,
    WorkoutSessionUpdate,
    FitnessSummary,
)


class FitnessService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = FitnessRepository(db)

    async def create_session(
        self, user_id: str, data: WorkoutSessionCreate
    ) -> WorkoutSession:
        session = WorkoutSession(
            user_id=user_id,
            title=data.title,
            session_date=data.session_date,
            duration_minutes=data.duration_minutes,
            notes=data.notes,
        )
        session.exercises = [
            Exercise(
                name=ex.name,
                sets=ex.sets,
                reps=ex.reps,
                weight_kg=ex.weight_kg,
                order=ex.order,
            )
            for ex in data.exercises
        ]
        return await self.repo.create(session)

    async def list_sessions(self, user_id: str) -> list[WorkoutSession]:
        return await self.repo.list_by_user(user_id)

    async def get_session(
        self, user_id: str, session_id: str
    ) -> WorkoutSession | None:
        return await self.repo.get_by_id(session_id, user_id)

    async def update_session(
        self, session: WorkoutSession, data: WorkoutSessionUpdate
    ) -> WorkoutSession:
        update_data = data.model_dump(exclude_unset=True, exclude={"exercises"})
        for key, value in update_data.items():
            setattr(session, key, value)

        if data.exercises is not None:
            # Reasignar la colección: el cascade delete-orphan borra las viejas
            # e inserta las nuevas en un solo commit. Hacer un bulk-delete aparte
            # dejaba la colección en memoria desincronizada y reinsertaba las viejas.
            session.exercises = [
                Exercise(
                    name=ex.name,
                    sets=ex.sets,
                    reps=ex.reps,
                    weight_kg=ex.weight_kg,
                    order=ex.order,
                )
                for ex in data.exercises
            ]

        return await self.repo.update(session)

    async def delete_session(self, session: WorkoutSession) -> None:
        await self.repo.delete(session)

    async def get_summary(self, user_id: str) -> FitnessSummary:
        today = date.today()
        start_of_month = today.replace(day=1)
        sessions_this_month = await self.repo.count_sessions_since(
            user_id, start_of_month
        )
        total_exercises = await self.repo.count_total_exercises(user_id)
        last_session_date = await self.repo.get_last_session_date(user_id)
        return FitnessSummary(
            sessions_this_month=sessions_this_month,
            total_exercises=total_exercises,
            last_session_date=last_session_date,
        )

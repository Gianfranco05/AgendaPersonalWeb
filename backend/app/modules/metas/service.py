import calendar
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.metas.models import Goal, HabitRecord
from app.modules.metas.repository import GoalRepository
from app.modules.metas.schemas import (
    GoalCreate,
    GoalUpdate,
    GoalProgress,
    MonthlySummaryItem,
)


class GoalsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = GoalRepository(db)

    async def create_goal(self, user_id: str, data: GoalCreate) -> Goal:
        goal = Goal(
            user_id=user_id,
            title=data.title,
            description=data.description,
            goal_type=data.goal_type,
            target_value=data.target_value,
            current_value=0,
            unit=data.unit,
            color=data.color,
            icon=data.icon,
            start_date=data.start_date,
            end_date=data.end_date,
        )
        return await self.repo.create(goal)

    async def list_active_goals(self, user_id: str) -> list[Goal]:
        return await self.repo.list_active(user_id)

    async def list_completed_goals(self, user_id: str) -> list[Goal]:
        return await self.repo.list_completed(user_id)

    async def get_goal(self, user_id: str, goal_id: str) -> Goal | None:
        return await self.repo.get_by_id(goal_id, user_id)

    async def update_goal(self, goal: Goal, data: GoalUpdate) -> Goal:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(goal, key, value)
        return await self.repo.update(goal)

    async def complete_goal(self, goal: Goal) -> Goal:
        goal.is_completed = True
        goal.current_value = goal.target_value
        return await self.repo.update(goal)

    async def delete_goal(self, goal: Goal) -> None:
        await self.repo.delete(goal)

    async def checkin_habit(
        self, user_id: str, goal_id: str, value: float, notes: str | None
    ) -> HabitRecord:
        today = date.today()
        record = await self.repo.get_today_record(goal_id, user_id, today)

        if record:
            record.value = value
            record.notes = notes
            await self.db.commit()
            await self.db.refresh(record)
        else:
            record = HabitRecord(
                user_id=user_id,
                goal_id=goal_id,
                record_date=today,
                value=value,
                notes=notes,
            )
            record = await self.repo.add_checkin(record)

        goal = await self.repo.get_by_id(goal_id, user_id)
        if goal:
            goal.current_value = goal.current_value + value
            if goal.goal_type == "binary" and goal.current_value >= goal.target_value:
                days_diff = (
                    goal.end_date or (date.today() + timedelta(days=365))
                ) - (goal.start_date or date.today())
                if days_diff.days > 0:
                    goal.is_completed = True
            await self.db.commit()
            await self.db.refresh(goal)

        return record

    async def get_progress(self, goal: Goal) -> GoalProgress:
        percentage = (
            min(100, (goal.current_value / goal.target_value * 100))
            if goal.target_value and goal.target_value > 0
            else 0
        )
        streak = await self.get_streak(goal.id, goal.user_id)
        return GoalProgress(
            current_value=goal.current_value,
            target_value=goal.target_value,
            percentage=percentage,
            streak=streak,
        )

    async def set_habit_value(
        self,
        user_id: str,
        goal_id: str,
        record_date: date,
        value: float,
        notes: str | None,
    ) -> HabitRecord:
        existing = await self.repo.get_record_by_date(goal_id, user_id, record_date)
        if existing:
            existing.value = value
            existing.notes = notes
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        record = HabitRecord(
            user_id=user_id,
            goal_id=goal_id,
            record_date=record_date,
            value=value,
            notes=notes,
        )
        return await self.repo.add_checkin(record)

    async def get_month_records(
        self, goal_id: str, user_id: str, year: int, month: int
    ) -> list[HabitRecord]:
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        return await self.repo.get_records_in_range(goal_id, user_id, start, end)

    async def get_monthly_summary(
        self, user_id: str, year: int, month: int
    ) -> list[MonthlySummaryItem]:
        start = date(year, month, 1)
        days_in_month = calendar.monthrange(year, month)[1]
        end = date(year, month, days_in_month)
        rows = await self.repo.get_monthly_summary(user_id, start, end)
        return [
            MonthlySummaryItem(
                goal_id=row.id,
                title=row.title,
                unit=row.unit,
                total=float(row.total),
                average=float(row.total) / days_in_month,
            )
            for row in rows
        ]

    async def get_streak(self, goal_id: str, user_id: str) -> int:
        records = await self.repo.get_recent_records(goal_id, user_id, days=30)
        dates = [r.record_date for r in records]
        if not dates:
            return 0
        unique_dates = sorted(set(dates), reverse=True)
        today = date.today()
        start = today if today in unique_dates else today - timedelta(days=1)
        streak = 0
        expected = start
        for d in unique_dates:
            if d == expected:
                streak += 1
                expected -= timedelta(days=1)
            elif d < expected:
                break
        return streak

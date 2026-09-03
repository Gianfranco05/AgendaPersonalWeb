from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.recordatorios.models import Reminder


class ReminderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_reminders(self, user_id: str) -> list[Reminder]:
        result = await self.db.execute(
            select(Reminder)
            .where(Reminder.user_id == user_id)
            .order_by(Reminder.hour, Reminder.minute)
        )
        return list(result.scalars().all())

    async def _get(self, user_id: str, reminder_id: str) -> Reminder:
        result = await self.db.execute(
            select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user_id)
        )
        reminder = result.scalar_one_or_none()
        if reminder is None:
            raise HTTPException(status_code=404, detail="Recordatorio no encontrado")
        return reminder

    async def create_reminder(
        self,
        user_id: str,
        message: str,
        hour: int,
        minute: int = 0,
        icon: str = "🔔",
        enabled: bool = True,
    ) -> Reminder:
        reminder = Reminder(
            user_id=user_id,
            message=message,
            icon=icon or "🔔",
            hour=hour,
            minute=minute,
            enabled=enabled,
        )
        self.db.add(reminder)
        await self.db.commit()
        await self.db.refresh(reminder)
        return reminder

    async def update_reminder(self, user_id: str, reminder_id: str, changes: dict) -> Reminder:
        reminder = await self._get(user_id, reminder_id)
        for field, value in changes.items():
            if value is not None:
                setattr(reminder, field, value)
        await self.db.commit()
        await self.db.refresh(reminder)
        return reminder

    async def delete_reminder(self, user_id: str, reminder_id: str) -> None:
        reminder = await self._get(user_id, reminder_id)
        await self.db.delete(reminder)
        await self.db.commit()

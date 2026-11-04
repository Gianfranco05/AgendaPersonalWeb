from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud_service import apply_changes, get_by_id_or_404
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
        return await get_by_id_or_404(
            self.db, Reminder, reminder_id, user_id, not_found_detail="Recordatorio no encontrado"
        )

    async def create_reminder(
        self,
        user_id: str,
        message: str,
        hour: int,
        minute: int = 0,
        icon: str = "🔔",
        enabled: bool = True,
        timezone_offset_minutes: Optional[int] = None,
    ) -> Reminder:
        reminder = Reminder(
            user_id=user_id,
            message=message,
            icon=icon or "🔔",
            hour=hour,
            minute=minute,
            enabled=enabled,
            timezone_offset_minutes=timezone_offset_minutes,
        )
        self.db.add(reminder)
        await self.db.commit()
        await self.db.refresh(reminder)
        return reminder

    async def update_reminder(self, user_id: str, reminder_id: str, changes: dict) -> Reminder:
        reminder = await self._get(user_id, reminder_id)
        apply_changes(reminder, changes)
        await self.db.commit()
        await self.db.refresh(reminder)
        return reminder

    async def delete_reminder(self, user_id: str, reminder_id: str) -> None:
        reminder = await self._get(user_id, reminder_id)
        await self.db.delete(reminder)
        await self.db.commit()

from datetime import datetime, date
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.eventos.models import Event
from app.modules.eventos.repository import EventRepository
from app.modules.eventos.schemas import EventCreate, EventUpdate


class EventosService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.event_repo = EventRepository(db)

    async def create_event(self, user_id: UUID, data: EventCreate) -> Event:
        event = Event(
            user_id=user_id,
            title=data.title,
            description=data.description,
            start_datetime=data.start_datetime,
            end_datetime=data.end_datetime,
            is_all_day=data.is_all_day,
            color=data.color,
            location=data.location,
            recurrence_rule=data.recurrence_rule,
            reminder_minutes=data.reminder_minutes,
        )
        return await self.event_repo.create(event)

    async def get_events(
        self,
        user_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Sequence[Event]:
        return await self.event_repo.get_all(user_id, date_from, date_to)

    async def get_event(self, event_id: UUID, user_id: UUID) -> Optional[Event]:
        return await self.event_repo.get_by_id(event_id, user_id)

    async def update_event(self, event: Event, data: EventUpdate) -> Event:
        if data.title is not None:
            event.title = data.title
        if data.description is not None:
            event.description = data.description
        if data.start_datetime is not None:
            event.start_datetime = data.start_datetime
        if data.end_datetime is not None:
            event.end_datetime = data.end_datetime
        if data.is_all_day is not None:
            event.is_all_day = data.is_all_day
        if data.color is not None:
            event.color = data.color
        if data.location is not None:
            event.location = data.location
        if data.recurrence_rule is not None:
            event.recurrence_rule = data.recurrence_rule
        if data.reminder_minutes is not None:
            event.reminder_minutes = data.reminder_minutes

        return await self.event_repo.update(event)

    async def delete_event(self, event: Event) -> None:
        await self.event_repo.delete(event)

    async def get_upcoming_events(
        self, user_id: UUID, limit: int = 5
    ) -> Sequence[Event]:
        return await self.event_repo.get_upcoming(user_id, limit)

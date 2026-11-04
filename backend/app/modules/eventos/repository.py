from datetime import datetime, date, time, timezone
from typing import Sequence, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.eventos.models import Event


class EventRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        user_id: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Sequence[Event]:
        query = select(Event).where(Event.user_id == user_id)

        # Limites aware en UTC: start_datetime es timestamptz y asyncpg toma un
        # datetime naive como hora local del servidor, asi que el filtro
        # cambiaba segun la zona horaria de la maquina que corre el backend.
        if date_from:
            query = query.where(
                Event.start_datetime >= datetime.combine(date_from, time.min, tzinfo=timezone.utc)
            )
        if date_to:
            query = query.where(
                Event.start_datetime <= datetime.combine(date_to, time.max, tzinfo=timezone.utc)
            )

        query = query.order_by(Event.start_datetime.asc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_id(self, event_id: str, user_id: str) -> Optional[Event]:
        result = await self.db.execute(
            select(Event).where(and_(Event.id == event_id, Event.user_id == user_id))
        )
        return result.scalar_one_or_none()

    async def get_upcoming(self, user_id: str, limit: int = 5) -> Sequence[Event]:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Event)
            .where(
                and_(
                    Event.user_id == user_id,
                    Event.start_datetime >= now,
                )
            )
            .order_by(Event.start_datetime.asc())
            .limit(limit)
        )
        return result.scalars().all()

    async def create(self, event: Event) -> Event:
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def update(self, event: Event) -> Event:
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def delete(self, event: Event) -> None:
        await self.db.delete(event)
        await self.db.commit()

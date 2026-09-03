from datetime import date
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.viajes.models import TRIP_STATUSES, PackingItem, Trip, TripStatus


class TravelService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _validate_status(self, status: Optional[str]) -> None:
        if status is not None and status not in TRIP_STATUSES:
            raise HTTPException(status_code=422, detail="Estado de viaje inválido")

    # ── Viajes ───────────────────────────────────────────────────────────────

    async def list_trips(self, user_id: str) -> list[Trip]:
        result = await self.db.execute(
            select(Trip).where(Trip.user_id == user_id).order_by(Trip.start_date.is_(None), Trip.start_date)
        )
        return list(result.scalars().all())

    async def _get_trip(self, user_id: str, trip_id: str) -> Trip:
        result = await self.db.execute(
            select(Trip).where(Trip.id == trip_id, Trip.user_id == user_id)
        )
        trip = result.scalar_one_or_none()
        if trip is None:
            raise HTTPException(status_code=404, detail="Viaje no encontrado")
        return trip

    async def create_trip(
        self,
        user_id: str,
        destination: str,
        start_date=None,
        end_date=None,
        status: Optional[str] = None,
        budget: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Trip:
        self._validate_status(status)
        trip = Trip(
            user_id=user_id,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            status=status or TripStatus.PLANEADO,
            budget=budget,
            notes=notes or None,
        )
        self.db.add(trip)
        await self.db.commit()
        await self.db.refresh(trip)
        return trip

    async def update_trip(self, user_id: str, trip_id: str, changes: dict) -> Trip:
        trip = await self._get_trip(user_id, trip_id)
        self._validate_status(changes.get("status"))
        for field, value in changes.items():
            if value is not None:
                setattr(trip, field, value)
        await self.db.commit()
        await self.db.refresh(trip)
        return trip

    async def delete_trip(self, user_id: str, trip_id: str) -> None:
        trip = await self._get_trip(user_id, trip_id)
        # El checklist se borra explicitamente: no hay ON DELETE CASCADE y
        # SQLite ni siquiera aplica las foreign keys.
        await self.db.execute(delete(PackingItem).where(PackingItem.trip_id == trip.id))
        await self.db.delete(trip)
        await self.db.commit()

    # ── Equipaje ─────────────────────────────────────────────────────────────

    async def list_items(self, user_id: str, trip_id: str) -> list[PackingItem]:
        await self._get_trip(user_id, trip_id)  # valida que el viaje sea del usuario
        result = await self.db.execute(
            select(PackingItem)
            .where(PackingItem.trip_id == trip_id, PackingItem.user_id == user_id)
            .order_by(PackingItem.created_at)
        )
        return list(result.scalars().all())

    async def _get_item(self, user_id: str, item_id: str) -> PackingItem:
        result = await self.db.execute(
            select(PackingItem).where(PackingItem.id == item_id, PackingItem.user_id == user_id)
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise HTTPException(status_code=404, detail="Item no encontrado")
        return item

    async def add_item(self, user_id: str, trip_id: str, name: str) -> PackingItem:
        await self._get_trip(user_id, trip_id)
        item = PackingItem(user_id=user_id, trip_id=trip_id, name=name)
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def set_packed(self, user_id: str, item_id: str, packed: bool) -> PackingItem:
        item = await self._get_item(user_id, item_id)
        item.packed = packed
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_item(self, user_id: str, item_id: str) -> None:
        item = await self._get_item(user_id, item_id)
        await self.db.delete(item)
        await self.db.commit()

    # ── Resumen ──────────────────────────────────────────────────────────────

    async def summary(self, user_id: str) -> dict:
        trips = await self.list_trips(user_id)
        upcoming = [
            t for t in trips if t.status in (TripStatus.PLANEADO, TripStatus.EN_CURSO)
        ]
        upcoming.sort(key=lambda t: (t.start_date is None, t.start_date or date.max))

        return {
            "total": len(trips),
            "planeados": sum(1 for t in trips if t.status == TripStatus.PLANEADO),
            "completados": sum(1 for t in trips if t.status == TripStatus.COMPLETADO),
            "next_trip": upcoming[0] if upcoming else None,
        }

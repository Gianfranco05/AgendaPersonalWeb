from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vehiculo.models import RECORD_TYPES, MaintenanceRecord, Vehicle


class VehicleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _validate_type(self, record_type: Optional[str]) -> None:
        if record_type is not None and record_type not in RECORD_TYPES:
            raise HTTPException(status_code=422, detail="Tipo de registro inválido")

    # ── Vehiculos ────────────────────────────────────────────────────────────

    async def list_vehicles(self, user_id: str) -> list[Vehicle]:
        result = await self.db.execute(
            select(Vehicle).where(Vehicle.user_id == user_id).order_by(Vehicle.name)
        )
        return list(result.scalars().all())

    async def _get_vehicle(self, user_id: str, vehicle_id: str) -> Vehicle:
        result = await self.db.execute(
            select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.user_id == user_id)
        )
        vehicle = result.scalar_one_or_none()
        if vehicle is None:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")
        return vehicle

    async def create_vehicle(
        self,
        user_id: str,
        name: str,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        plate: Optional[str] = None,
    ) -> Vehicle:
        vehicle = Vehicle(user_id=user_id, name=name, brand=brand or None, model=model or None, plate=plate or None)
        self.db.add(vehicle)
        await self.db.commit()
        await self.db.refresh(vehicle)
        return vehicle

    async def update_vehicle(self, user_id: str, vehicle_id: str, changes: dict) -> Vehicle:
        vehicle = await self._get_vehicle(user_id, vehicle_id)
        for field, value in changes.items():
            if value is not None:
                setattr(vehicle, field, value)
        await self.db.commit()
        await self.db.refresh(vehicle)
        return vehicle

    async def delete_vehicle(self, user_id: str, vehicle_id: str) -> None:
        vehicle = await self._get_vehicle(user_id, vehicle_id)
        # El historial se borra explicitamente: no hay ON DELETE CASCADE y
        # SQLite ni siquiera aplica las foreign keys.
        await self.db.execute(
            delete(MaintenanceRecord).where(MaintenanceRecord.vehicle_id == vehicle.id)
        )
        await self.db.delete(vehicle)
        await self.db.commit()

    # ── Historial ────────────────────────────────────────────────────────────

    async def list_records(
        self, user_id: str, vehicle_id: Optional[str] = None, record_type: Optional[str] = None
    ) -> list[MaintenanceRecord]:
        self._validate_type(record_type)
        if vehicle_id:
            await self._get_vehicle(user_id, vehicle_id)  # valida ownership
        query = select(MaintenanceRecord).where(MaintenanceRecord.user_id == user_id)
        if vehicle_id:
            query = query.where(MaintenanceRecord.vehicle_id == vehicle_id)
        if record_type:
            query = query.where(MaintenanceRecord.record_type == record_type)
        result = await self.db.execute(query.order_by(MaintenanceRecord.record_date.desc()))
        return list(result.scalars().all())

    async def _get_record(self, user_id: str, record_id: str) -> MaintenanceRecord:
        result = await self.db.execute(
            select(MaintenanceRecord).where(
                MaintenanceRecord.id == record_id, MaintenanceRecord.user_id == user_id
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        return record

    async def create_record(
        self,
        user_id: str,
        vehicle_id: str,
        record_type: str,
        record_date,
        cost: Optional[float] = None,
        odometer_km: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> MaintenanceRecord:
        await self._get_vehicle(user_id, vehicle_id)  # valida que el vehiculo sea del usuario
        self._validate_type(record_type)
        record = MaintenanceRecord(
            user_id=user_id,
            vehicle_id=vehicle_id,
            record_type=record_type,
            record_date=record_date,
            cost=cost,
            odometer_km=odometer_km,
            notes=notes or None,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def delete_record(self, user_id: str, record_id: str) -> None:
        record = await self._get_record(user_id, record_id)
        await self.db.delete(record)
        await self.db.commit()

    # ── Resumen ──────────────────────────────────────────────────────────────

    async def summary(self, user_id: str) -> dict:
        vehicles = await self.list_vehicles(user_id)
        records = await self.list_records(user_id)
        total_spent = sum(r.cost for r in records if r.cost is not None)

        return {
            "vehicles_total": len(vehicles),
            "records_total": len(records),
            "total_spent": round(total_spent, 2) if records else 0.0,
            "last_record": records[0] if records else None,
        }

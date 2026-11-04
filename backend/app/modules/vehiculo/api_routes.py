from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.entitlements import require_module
from app.database import get_db
from app.modules.auth.models import User
from app.modules.vehiculo.service import VehicleService

# Plantilla de pago: sin la compra, el server no deja tocar estos endpoints.
router = APIRouter(
    prefix="/vehicle", tags=["vehicle"], dependencies=[Depends(require_module("vehicle"))]
)


class VehicleOut(BaseModel):
    id: str
    name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    plate: Optional[str] = None

    model_config = {"from_attributes": True}


class VehicleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    brand: Optional[str] = Field(default=None, max_length=80)
    model: Optional[str] = Field(default=None, max_length=80)
    plate: Optional[str] = Field(default=None, max_length=20)


class VehicleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    brand: Optional[str] = Field(default=None, max_length=80)
    model: Optional[str] = Field(default=None, max_length=80)
    plate: Optional[str] = Field(default=None, max_length=20)


class RecordOut(BaseModel):
    id: str
    vehicle_id: str
    record_type: str
    record_date: date
    cost: Optional[float] = None
    odometer_km: Optional[int] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class RecordCreate(BaseModel):
    vehicle_id: str
    record_type: str
    record_date: date
    cost: Optional[float] = Field(default=None, ge=0)
    odometer_km: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=1000)


class VehicleSummaryOut(BaseModel):
    vehicles_total: int
    records_total: int
    total_spent: float
    last_record: Optional[RecordOut] = None


@router.get("/vehicles", response_model=list[VehicleOut])
async def list_vehicles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await VehicleService(db).list_vehicles(str(current_user.id))


@router.post("/vehicles", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    body: VehicleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await VehicleService(db).create_vehicle(
        str(current_user.id), body.name, body.brand, body.model, body.plate
    )


@router.patch("/vehicles/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(
    vehicle_id: str,
    body: VehicleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await VehicleService(db).update_vehicle(
        str(current_user.id), vehicle_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/vehicles/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await VehicleService(db).delete_vehicle(str(current_user.id), vehicle_id)


@router.get("/records", response_model=list[RecordOut])
async def list_records(
    vehicle_id: Optional[str] = Query(None),
    record_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await VehicleService(db).list_records(str(current_user.id), vehicle_id, record_type)


@router.post("/records", response_model=RecordOut, status_code=status.HTTP_201_CREATED)
async def create_record(
    body: RecordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await VehicleService(db).create_record(
        str(current_user.id),
        body.vehicle_id,
        body.record_type,
        body.record_date,
        body.cost,
        body.odometer_km,
        body.notes,
    )


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    record_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await VehicleService(db).delete_record(str(current_user.id), record_id)


@router.get("/summary", response_model=VehicleSummaryOut)
async def get_vehicle_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await VehicleService(db).summary(str(current_user.id))

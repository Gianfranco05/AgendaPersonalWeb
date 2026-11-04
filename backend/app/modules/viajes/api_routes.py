from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.entitlements import require_module
from app.database import get_db
from app.modules.auth.models import User
from app.modules.viajes.service import TravelService

# Plantilla de pago: sin la compra, el server no deja tocar estos endpoints.
router = APIRouter(
    prefix="/travel", tags=["travel"], dependencies=[Depends(require_module("travel"))]
)


class TripOut(BaseModel):
    id: str
    destination: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str
    budget: Optional[float] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class TripCreate(BaseModel):
    destination: str = Field(min_length=1, max_length=160)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    budget: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=1000)


class TripUpdate(BaseModel):
    destination: Optional[str] = Field(default=None, min_length=1, max_length=160)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    budget: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=1000)


class PackingItemOut(BaseModel):
    id: str
    trip_id: str
    name: str
    packed: bool

    model_config = {"from_attributes": True}


class PackingItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class PackingItemUpdate(BaseModel):
    packed: bool


class TravelSummaryOut(BaseModel):
    total: int
    planeados: int
    completados: int
    next_trip: Optional[TripOut] = None


@router.get("/trips", response_model=list[TripOut])
async def list_trips(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await TravelService(db).list_trips(str(current_user.id))


@router.post("/trips", response_model=TripOut, status_code=status.HTTP_201_CREATED)
async def create_trip(
    body: TripCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await TravelService(db).create_trip(
        str(current_user.id),
        body.destination,
        body.start_date,
        body.end_date,
        body.status,
        body.budget,
        body.notes,
    )


@router.patch("/trips/{trip_id}", response_model=TripOut)
async def update_trip(
    trip_id: str,
    body: TripUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await TravelService(db).update_trip(
        str(current_user.id), trip_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/trips/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await TravelService(db).delete_trip(str(current_user.id), trip_id)


@router.get("/trips/{trip_id}/items", response_model=list[PackingItemOut])
async def list_items(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await TravelService(db).list_items(str(current_user.id), trip_id)


@router.post(
    "/trips/{trip_id}/items", response_model=PackingItemOut, status_code=status.HTTP_201_CREATED
)
async def add_item(
    trip_id: str,
    body: PackingItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await TravelService(db).add_item(str(current_user.id), trip_id, body.name)


@router.patch("/items/{item_id}", response_model=PackingItemOut)
async def set_item_packed(
    item_id: str,
    body: PackingItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await TravelService(db).set_packed(str(current_user.id), item_id, body.packed)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await TravelService(db).delete_item(str(current_user.id), item_id)


@router.get("/summary", response_model=TravelSummaryOut)
async def get_travel_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await TravelService(db).summary(str(current_user.id))

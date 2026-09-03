from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.entitlements import require_module
from app.database import get_db
from app.modules.auth.models import User
from app.modules.peliculas.service import MediaService

# Plantilla de pago: sin la compra, el server no deja tocar estos endpoints.
router = APIRouter(
    prefix="/media", tags=["media"], dependencies=[Depends(require_module("media"))]
)


class MediaItemOut(BaseModel):
    id: str
    title: str
    media_type: str
    status: str
    rating: Optional[float] = None
    year: Optional[int] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class MediaItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    media_type: Optional[str] = None
    status: Optional[str] = None
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    year: Optional[int] = Field(default=None, ge=1878, le=2200)
    notes: Optional[str] = Field(default=None, max_length=1000)


class MediaItemUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    media_type: Optional[str] = None
    status: Optional[str] = None
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    year: Optional[int] = Field(default=None, ge=1878, le=2200)
    notes: Optional[str] = Field(default=None, max_length=1000)


class MediaSummaryOut(BaseModel):
    total: int
    pendientes: int
    viendo: int
    vistos: int
    average_rating: Optional[float] = None


@router.get("/items", response_model=list[MediaItemOut])
async def list_items(
    status_filter: Optional[str] = Query(None, alias="status"),
    media_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MediaService(db).list_items(str(current_user.id), status_filter, media_type)


@router.post("/items", response_model=MediaItemOut, status_code=status.HTTP_201_CREATED)
async def create_item(
    body: MediaItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MediaService(db).create_item(
        str(current_user.id),
        body.title,
        body.media_type,
        body.status,
        body.rating,
        body.year,
        body.notes,
    )


@router.patch("/items/{item_id}", response_model=MediaItemOut)
async def update_item(
    item_id: str,
    body: MediaItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MediaService(db).update_item(
        str(current_user.id), item_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await MediaService(db).delete_item(str(current_user.id), item_id)


@router.get("/summary", response_model=MediaSummaryOut)
async def get_media_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await MediaService(db).summary(str(current_user.id))

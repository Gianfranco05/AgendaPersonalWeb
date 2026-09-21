from typing import Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.modules.auth.models import User
from app.modules.recordatorios.service import ReminderService

router = APIRouter(prefix="/reminders", tags=["reminders"])


class ReminderOut(BaseModel):
    id: str
    message: str
    icon: str
    hour: int
    minute: int
    enabled: bool

    model_config = {"from_attributes": True}


class ReminderCreate(BaseModel):
    message: str = Field(min_length=1, max_length=200)
    icon: Optional[str] = Field(default=None, max_length=8)
    hour: int = Field(ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)
    enabled: bool = True
    # Minutos al este de UTC del dispositivo (mismo signo que tz_offset_minutes
    # en /api/v1/focus/summary). Opcional para no romper clientes viejos.
    timezone_offset_minutes: Optional[int] = Field(default=None, ge=-840, le=840)


class ReminderUpdate(BaseModel):
    message: Optional[str] = Field(default=None, min_length=1, max_length=200)
    icon: Optional[str] = Field(default=None, max_length=8)
    hour: Optional[int] = Field(default=None, ge=0, le=23)
    minute: Optional[int] = Field(default=None, ge=0, le=59)
    enabled: Optional[bool] = None
    timezone_offset_minutes: Optional[int] = Field(default=None, ge=-840, le=840)


@router.get("", response_model=list[ReminderOut])
async def list_reminders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ReminderService(db).list_reminders(str(current_user.id))


@router.post("", response_model=ReminderOut, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    body: ReminderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ReminderService(db).create_reminder(
        str(current_user.id),
        body.message,
        body.hour,
        body.minute,
        body.icon,
        body.enabled,
        body.timezone_offset_minutes,
    )


@router.patch("/{reminder_id}", response_model=ReminderOut)
async def update_reminder(
    reminder_id: str,
    body: ReminderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ReminderService(db).update_reminder(
        str(current_user.id), reminder_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ReminderService(db).delete_reminder(str(current_user.id), reminder_id)

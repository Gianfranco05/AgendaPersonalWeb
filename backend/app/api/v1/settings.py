from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.ajustes.models import UserPreference

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    currency: str
    theme_color: str
    date_format: str
    google_calendar_id: str

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    currency: Optional[str] = None
    theme_color: Optional[str] = None
    date_format: Optional[str] = None
    google_calendar_id: Optional[str] = None


@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == current_user.id)
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        prefs = UserPreference(user_id=current_user.id)
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)

    return SettingsResponse(
        currency=prefs.currency,
        theme_color=prefs.theme_color,
        date_format=prefs.date_format,
        google_calendar_id=prefs.google_calendar_id,
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(
    data: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == current_user.id)
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        prefs = UserPreference(user_id=current_user.id)
        db.add(prefs)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(prefs, key, value)

    await db.commit()
    await db.refresh(prefs)

    return SettingsResponse(
        currency=prefs.currency,
        theme_color=prefs.theme_color,
        date_format=prefs.date_format,
        google_calendar_id=prefs.google_calendar_id,
    )

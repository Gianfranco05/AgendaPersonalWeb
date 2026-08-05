from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.ajustes.models import UserPreference
from app.modules.ajustes.service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    currency: str
    theme_color: str
    date_format: str
    google_calendar_id: str
    google_connected: bool

    model_config = {"from_attributes": True}


def _to_response(prefs: UserPreference) -> "SettingsResponse":
    return SettingsResponse(
        currency=prefs.currency,
        theme_color=prefs.theme_color,
        date_format=prefs.date_format,
        google_calendar_id=prefs.google_calendar_id,
        google_connected=bool(prefs.google_refresh_token),
    )


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

    return _to_response(prefs)


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

    return _to_response(prefs)


class GoogleSyncResponse(BaseModel):
    synced: int


@router.post("/google/sync", response_model=GoogleSyncResponse)
async def sync_google_calendar(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SettingsService(db)
    prefs = await service.get_preferences(current_user.id)
    if not prefs.google_refresh_token:
        raise HTTPException(status_code=400, detail="Google Calendar no está conectado")

    try:
        count = await service.sync_events_to_google(current_user.id, prefs)
    except Exception:
        raise HTTPException(status_code=502, detail="Error al sincronizar con Google Calendar")

    return GoogleSyncResponse(synced=count)


@router.post("/google/disconnect", response_model=SettingsResponse)
async def disconnect_google_calendar(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SettingsService(db)
    prefs = await service.disconnect_google(current_user.id)
    return _to_response(prefs)

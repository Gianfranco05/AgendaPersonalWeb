from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.ajustes.models import UserPreference
from app.modules.ajustes.service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])

# Cotizacion manual (ARS por 1 USD / 1 EUR). Numeric(14, 4): hasta 9.999.999,9999.
FxRate = Annotated[
    Decimal, Field(gt=Decimal("0"), le=Decimal("9999999.9999"), decimal_places=4)
]
_FX_FIELDS = ("fx_usd_ars", "fx_eur_ars")
_RATE_QUANT = Decimal("0.0001")


def _rate(value) -> Optional[Decimal]:
    # SQLite devuelve la cotizacion sin los ceros finales (1450.5): se
    # normaliza a 4 decimales para que el contrato sea el mismo que en Postgres.
    return None if value is None else Decimal(str(value)).quantize(_RATE_QUANT)


class SettingsResponse(BaseModel):
    currency: str
    theme_color: str
    date_format: str
    google_calendar_id: str
    google_connected: bool
    fx_usd_ars: Optional[Decimal] = None
    fx_eur_ars: Optional[Decimal] = None
    fx_rates_updated_at: Optional[datetime] = None
    include_investments_in_balance: bool = False

    model_config = {"from_attributes": True}


def _to_response(prefs: UserPreference) -> "SettingsResponse":
    return SettingsResponse(
        currency=prefs.currency,
        theme_color=prefs.theme_color,
        date_format=prefs.date_format,
        google_calendar_id=prefs.google_calendar_id,
        google_connected=bool(prefs.google_refresh_token),
        fx_usd_ars=_rate(prefs.fx_usd_ars),
        fx_eur_ars=_rate(prefs.fx_eur_ars),
        fx_rates_updated_at=prefs.fx_rates_updated_at,
        include_investments_in_balance=bool(prefs.include_investments_in_balance),
    )


class SettingsUpdate(BaseModel):
    currency: Optional[str] = None
    theme_color: Optional[str] = None
    date_format: Optional[str] = None
    google_calendar_id: Optional[str] = None
    # null borra la cotizacion; `fx_rates_updated_at` lo pone el server.
    fx_usd_ars: Optional[FxRate] = None
    fx_eur_ars: Optional[FxRate] = None
    include_investments_in_balance: Optional[bool] = None


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
    # La columna no admite null: un null explicito se ignora.
    if update_data.get("include_investments_in_balance") is None:
        update_data.pop("include_investments_in_balance", None)

    rates_changed = any(
        key in update_data and _rate(update_data[key]) != _rate(getattr(prefs, key))
        for key in _FX_FIELDS
    )
    for key, value in update_data.items():
        setattr(prefs, key, value)
    if rates_changed:
        both_cleared = prefs.fx_usd_ars is None and prefs.fx_eur_ars is None
        prefs.fx_rates_updated_at = None if both_cleared else datetime.now(timezone.utc)

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

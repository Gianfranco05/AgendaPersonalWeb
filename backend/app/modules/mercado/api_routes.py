"""Datos de mercado para los clientes. Todo sale de la base: ninguna ruta
llama a las APIs externas (eso lo hace el scheduler)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user
from app.database import get_db
from app.modules.auth.models import User
from app.modules.mercado.crypto_assets import list_assets
from app.modules.mercado.rates import (
    FETCH_STALE_AFTER,
    KIND_LABELS,
    STALE_AFTER,
    fetch_is_stale,
)
from app.modules.mercado.repository import FxSnapshot, MarketRepository
from app.modules.mercado.inflation import month_key
from app.modules.mercado.schemas import (
    CryptoAssetOut,
    FxQuoteOut,
    InflationOut,
    InflationPointOut,
    MarketFxOut,
)

router = APIRouter(prefix="/finance/market", tags=["finance"])

#: Los tipos que ofrecen los clientes (se guardan mas, ver D2).
EXPOSED = {"USD": ("oficial", "mep", "blue"), "EUR": ("oficial", "blue")}


def _quotes(snapshot: FxSnapshot, currency: str, now: datetime) -> list[FxQuoteOut]:
    fetch_stale = fetch_is_stale(snapshot, now)
    out = []
    for kind in EXPOSED[currency]:
        quote = snapshot.quotes.get((currency, kind))
        if quote is None:
            continue
        out.append(
            FxQuoteOut(
                kind=kind,
                label=KIND_LABELS[kind],
                buy=quote.buy,
                sell=quote.sell,
                provider=quote.provider,
                as_of=quote.as_of,
                stale=now - quote.as_of > STALE_AFTER or fetch_stale,
            )
        )
    return out


@router.get("/fx", response_model=MarketFxOut)
async def get_market_fx(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    snapshot = await MarketRepository(db).fx_snapshot()
    now = datetime.now(timezone.utc)
    state = snapshot.state
    degraded = (
        state is None
        or state.last_success_at is None
        or state.consecutive_failures > 0
        or now - state.last_success_at > FETCH_STALE_AFTER
    )
    return MarketFxOut(
        usd=_quotes(snapshot, "USD", now),
        eur=_quotes(snapshot, "EUR", now),
        last_success_at=state.last_success_at if state else None,
        degraded=degraded,
    )


@router.get("/inflation", response_model=InflationOut)
async def get_market_inflation(
    months: int = Query(12, ge=1, le=120),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    series = await MarketRepository(db).inflation_series()
    if not series:
        return InflationOut(series=[])
    periods = sorted(series)
    last = periods[-1]
    return InflationOut(
        series=[InflationPointOut(period=month_key(p), pct=series[p]) for p in periods[-months:]],
        last_published_period=month_key(last),
        estimate_pct=series[last],
    )


@router.get("/crypto-assets", response_model=list[CryptoAssetOut])
async def get_crypto_assets(current_user: User = Depends(get_current_user)):
    if not settings.MARKET_CRYPTO_ENABLED:
        return []
    return [CryptoAssetOut(ticker=a.ticker, name=a.name) for a in list_assets()]

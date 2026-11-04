from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class FxQuoteOut(BaseModel):
    kind: str
    label: str
    buy: Optional[Decimal] = None
    #: La que se usa para convertir.
    sell: Decimal
    provider: str
    as_of: datetime
    stale: bool


class MarketFxOut(BaseModel):
    usd: list[FxQuoteOut]
    eur: list[FxQuoteOut]
    last_success_at: Optional[datetime] = None
    #: El ultimo intento fallo, o el ultimo exito tiene mas de 6 h (o nunca hubo).
    degraded: bool


class InflationPointOut(BaseModel):
    #: "2026-09"
    period: str
    pct: Decimal


class InflationOut(BaseModel):
    series: list[InflationPointOut]
    last_published_period: Optional[str] = None
    #: Variacion mensual con la que se estiman los meses sin publicar.
    estimate_pct: Optional[Decimal] = None


class CryptoAssetOut(BaseModel):
    ticker: str
    name: str

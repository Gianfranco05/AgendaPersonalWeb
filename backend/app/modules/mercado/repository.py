"""Acceso a las tablas de mercado y cache en proceso.

El cache guarda estructuras planas (no instancias del ORM, que quedan ligadas
a una sesion). Se invalida cuando el job de este mismo proceso escribe; entre
procesos alcanza con el TTL. Los tests ponen el TTL en 0 (ver conftest).
"""

import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.mercado.models import (
    FxQuote,
    InflationMonth,
    MarketFetchState,
    MarketPrice,
)

#: Argentina no tiene horario de verano: UTC-3 fijo.
AR_OFFSET = timedelta(hours=-3)

FX_CACHE_TTL_SECONDS = 60.0
INFLATION_CACHE_TTL_SECONDS = 600.0

SOURCES = ("fx", "inflation", "crypto")


def as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """SQLite devuelve los DateTime sin zona: se asumen UTC."""
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def ar_date(moment: datetime) -> date:
    return (as_utc(moment) + AR_OFFSET).date()


def to_dec(value) -> Optional[Decimal]:
    return None if value is None else Decimal(str(value))


@dataclass(frozen=True)
class QuoteView:
    currency: str
    kind: str
    buy: Optional[Decimal]
    sell: Decimal
    provider: str
    as_of: datetime
    fetched_at: datetime


@dataclass(frozen=True)
class FetchStateView:
    source: str
    next_run_at: Optional[datetime]
    last_attempt_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_error: Optional[str]
    consecutive_failures: int


@dataclass(frozen=True)
class FxSnapshot:
    quotes: dict[tuple[str, str], QuoteView]
    state: Optional[FetchStateView]


# ── Cache en proceso ────────────────────────────────────────────────────────

_cache: dict[str, tuple[float, object]] = {}


def clear_cache() -> None:
    _cache.clear()


def _cached(key: str, ttl: float):
    entry = _cache.get(key)
    if entry is not None and ttl > 0 and time.monotonic() - entry[0] < ttl:
        return entry[1]
    return None


def _store(key: str, value: object) -> None:
    _cache[key] = (time.monotonic(), value)


class MarketRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Cotizaciones ────────────────────────────────────────────────────────

    async def fx_snapshot(self) -> FxSnapshot:
        """Ultima cotizacion de cada `(moneda, tipo)` y estado del job `fx`."""
        cached = _cached("fx", FX_CACHE_TTL_SECONDS)
        if cached is not None:
            return cached  # type: ignore[return-value]
        latest = (
            select(
                FxQuote.currency.label("currency"),
                FxQuote.kind.label("kind"),
                func.max(FxQuote.quote_date).label("max_date"),
            )
            .group_by(FxQuote.currency, FxQuote.kind)
            .subquery()
        )
        rows = (
            await self.db.execute(
                select(FxQuote).join(
                    latest,
                    and_(
                        FxQuote.currency == latest.c.currency,
                        FxQuote.kind == latest.c.kind,
                        FxQuote.quote_date == latest.c.max_date,
                    ),
                )
            )
        ).scalars()
        quotes = {
            (q.currency, q.kind): QuoteView(
                currency=q.currency,
                kind=q.kind,
                buy=to_dec(q.buy),
                sell=Decimal(str(q.sell)),
                provider=q.provider,
                as_of=as_utc(q.source_updated_at),
                fetched_at=as_utc(q.fetched_at),
            )
            for q in rows
        }
        snapshot = FxSnapshot(quotes=quotes, state=await self.fetch_state("fx"))
        _store("fx", snapshot)
        return snapshot

    async def latest_quote(self, currency: str, kind: str) -> Optional[FxQuote]:
        result = await self.db.execute(
            select(FxQuote)
            .where(and_(FxQuote.currency == currency, FxQuote.kind == kind))
            .order_by(FxQuote.quote_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_day_quote(self, currency: str, kind: str, day: date) -> Optional[FxQuote]:
        result = await self.db.execute(
            select(FxQuote).where(
                and_(
                    FxQuote.currency == currency,
                    FxQuote.kind == kind,
                    FxQuote.quote_date == day,
                )
            )
        )
        return result.scalar_one_or_none()

    async def delete_quotes_before(self, cutoff: date) -> int:
        result = await self.db.execute(delete(FxQuote).where(FxQuote.quote_date < cutoff))
        return result.rowcount or 0

    # ── Inflacion ───────────────────────────────────────────────────────────

    async def inflation_rows(self) -> dict[date, InflationMonth]:
        result = await self.db.execute(select(InflationMonth))
        return {row.period: row for row in result.scalars()}

    async def inflation_series(self) -> dict[date, Decimal]:
        """`{periodo: variacion %}` (cache 10 min). Es lo unico que lee el
        calculo de rendimiento real."""
        cached = _cached("inflation", INFLATION_CACHE_TTL_SECONDS)
        if cached is not None:
            return cached  # type: ignore[return-value]
        result = await self.db.execute(select(InflationMonth.period, InflationMonth.pct))
        series = {period: Decimal(str(pct)) for period, pct in result.all()}
        _store("inflation", series)
        return series

    # ── Precios de activos ──────────────────────────────────────────────────

    async def get_price(self, provider: str, symbol: str, vs_currency: str) -> Optional[MarketPrice]:
        result = await self.db.execute(
            select(MarketPrice).where(
                and_(
                    MarketPrice.provider == provider,
                    MarketPrice.symbol == symbol,
                    MarketPrice.vs_currency == vs_currency,
                )
            )
        )
        return result.scalar_one_or_none()

    # ── Estado / lease del scheduler ────────────────────────────────────────

    async def fetch_state(self, source: str) -> Optional[FetchStateView]:
        row = await self.db.get(MarketFetchState, source)
        if row is None:
            return None
        return FetchStateView(
            source=row.source,
            next_run_at=as_utc(row.next_run_at),
            last_attempt_at=as_utc(row.last_attempt_at),
            last_success_at=as_utc(row.last_success_at),
            last_error=row.last_error,
            consecutive_failures=row.consecutive_failures or 0,
        )

    async def try_acquire_lease(self, source: str, now: datetime, lease_seconds: int) -> bool:
        """Lease atomico: solo una llamada (de cualquier worker) logra cambiar
        la fila cuando toca correr y nadie tiene el lease vigente."""
        result = await self.db.execute(
            update(MarketFetchState)
            .where(
                and_(
                    MarketFetchState.source == source,
                    MarketFetchState.next_run_at <= now,
                    (MarketFetchState.lease_until.is_(None))
                    | (MarketFetchState.lease_until < now),
                )
            )
            .values(lease_until=now + timedelta(seconds=lease_seconds), last_attempt_at=now)
        )
        await self.db.commit()
        return result.rowcount == 1

    async def finish(
        self,
        source: str,
        *,
        now: datetime,
        next_run_at: datetime,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        row = await self.db.get(MarketFetchState, source)
        if row is None:
            return
        row.lease_until = None
        row.next_run_at = next_run_at
        if success:
            row.consecutive_failures = 0
            row.last_success_at = now
            row.last_error = None
        else:
            row.consecutive_failures = (row.consecutive_failures or 0) + 1
            row.last_error = (error or "error")[:300]
        await self.db.commit()
        clear_cache()

    async def schedule_now(self, source: str, now: datetime) -> None:
        """Pide que el proximo ciclo del scheduler consulte `source` ya."""
        await self.db.execute(
            update(MarketFetchState)
            .where(MarketFetchState.source == source)
            .values(next_run_at=now)
        )
        await self.db.commit()

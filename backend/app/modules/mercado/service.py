"""Jobs de obtencion de datos de mercado (dolar e inflacion) y estado de las
fuentes. Los jobs reciben el `httpx.AsyncClient` y la sesion por parametro:
primero consultan la red (sin transaccion abierta) y recien despues escriben."""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.mercado.models import FxQuote, InflationMonth, MarketFetchState
from app.modules.mercado.providers import argentinadatos, bluelytics, datos_gob, dolarapi
from app.modules.mercado.providers.argentinadatos import InflationIn
from app.modules.mercado.providers.base import FxQuoteIn, ProviderError
from app.modules.mercado.repository import (
    SOURCES,
    MarketRepository,
    ar_date,
    as_utc,
    clear_cache,
)

logger = logging.getLogger(__name__)

MAX_SELL = Decimal("10000000")
MAX_JUMP = Decimal("0.5")
BUY_VS_SELL = Decimal("1.5")
RETENTION_DAYS = 730

#: Tipos de dolar que tienen respaldo en ArgentinaDatos.
USD_BACKUP_KINDS = ("oficial", "mep", "blue")

_last_retention: Optional[date] = None


@dataclass
class FxRefreshResult:
    stored: int = 0
    discarded: int = 0
    fetched: int = 0
    errors: list[str] = field(default_factory=list)


async def ensure_state_rows(db: AsyncSession) -> None:
    """Crea las filas de `market_fetch_state` que falten (la migracion las
    siembra; con `create_all`, tests y dev, las crea el primer ciclo). Sin
    `ON CONFLICT`: dos workers pueden competir y el que pierde atrapa el error."""
    existing = set((await db.execute(select(MarketFetchState.source))).scalars())
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    for source in SOURCES:
        if source in existing:
            continue
        db.add(MarketFetchState(source=source, next_run_at=epoch, consecutive_failures=0))
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()


# ── Dolar ───────────────────────────────────────────────────────────────────


def _sane(quote: FxQuoteIn, last_sell: Optional[Decimal]) -> bool:
    if quote.sell <= 0 or quote.sell > MAX_SELL:
        return False
    if quote.buy is not None and quote.buy > quote.sell * BUY_VS_SELL:
        return False
    if last_sell is not None and last_sell > 0:
        if abs(quote.sell - last_sell) / last_sell > MAX_JUMP:
            return False
    return True


async def _try(awaitable, errors: list[str], label: str) -> list[FxQuoteIn]:
    try:
        return await awaitable
    except ProviderError as exc:
        logger.warning("Fallo %s: %s", label, exc)
        errors.append(f"{label}: {exc}")
        return []


async def fetch_fx_quotes(client: httpx.AsyncClient) -> tuple[list[FxQuoteIn], list[str]]:
    """Primario + cadena de respaldo (D3). Un respaldo solo aporta los pares
    que el anterior no trajo, asi un proveedor mas rapido no pisa al primario."""
    errors: list[str] = []
    chosen: dict[tuple[str, str], FxQuoteIn] = {}

    def take(quotes: list[FxQuoteIn], allowed: Optional[set[tuple[str, str]]] = None) -> None:
        for quote in quotes:
            key = (quote.currency, quote.kind)
            if key in chosen or (allowed is not None and key not in allowed):
                continue
            chosen[key] = quote

    take(await _try(dolarapi.fetch_usd(client), errors, "DolarAPI dolares"))
    take(await _try(dolarapi.fetch_eur(client), errors, "DolarAPI euro"))

    # Bluelytics: oficial/blue de USD y EUR; el EUR blue solo sale de aca.
    backup_pairs = {
        ("USD", "oficial"),
        ("USD", "blue"),
        ("EUR", "oficial"),
        ("EUR", "blue"),
    }
    if any(pair not in chosen for pair in backup_pairs):
        take(await _try(bluelytics.fetch(client), errors, "Bluelytics"), backup_pairs)

    for kind in USD_BACKUP_KINDS:
        if ("USD", kind) not in chosen:
            take(
                await _try(argentinadatos.fetch_fx(client, kind), errors, f"ArgentinaDatos {kind}"),
                {("USD", kind)},
            )
    return list(chosen.values()), errors


async def store_fx_quotes(
    db: AsyncSession, quotes: list[FxQuoteIn], now: datetime
) -> FxRefreshResult:
    repo = MarketRepository(db)
    result = FxRefreshResult(fetched=len(quotes))
    for quote in quotes:
        latest = await repo.latest_quote(quote.currency, quote.kind)
        last_sell = Decimal(str(latest.sell)) if latest is not None else None
        if not _sane(quote, last_sell):
            logger.warning(
                "Cotizacion descartada por sanidad: %s %s sell=%s (ultima=%s)",
                quote.currency,
                quote.kind,
                quote.sell,
                last_sell,
            )
            result.discarded += 1
            continue
        day = ar_date(quote.source_updated_at)
        existing = (
            latest
            if latest is not None and latest.quote_date == day
            else await repo.get_day_quote(quote.currency, quote.kind, day)
        )
        buy = quote.buy if quote.buy is not None and quote.buy > 0 else None
        if existing is None:
            db.add(
                FxQuote(
                    currency=quote.currency,
                    kind=quote.kind,
                    quote_date=day,
                    buy=buy,
                    sell=quote.sell,
                    provider=quote.provider,
                    source_updated_at=quote.source_updated_at,
                    fetched_at=now,
                )
            )
            result.stored += 1
        elif as_utc(existing.source_updated_at) < quote.source_updated_at:
            existing.buy = buy
            existing.sell = quote.sell
            existing.provider = quote.provider
            existing.source_updated_at = quote.source_updated_at
            existing.fetched_at = now
            result.stored += 1
        # Si no es mas nueva, queda lo guardado (un respaldo atrasado no pisa).
        await db.flush()
    await db.commit()
    clear_cache()
    return result


async def _prune_old_quotes(db: AsyncSession, today: date) -> None:
    global _last_retention
    if _last_retention == today:
        return
    await MarketRepository(db).delete_quotes_before(today - timedelta(days=RETENTION_DAYS))
    await db.commit()
    _last_retention = today


async def refresh_fx(
    db: AsyncSession, client: httpx.AsyncClient, now: Optional[datetime] = None
) -> FxRefreshResult:
    """Un ciclo del job `fx`. Levanta `ProviderError` si no se obtuvo nada."""
    now = now or datetime.now(timezone.utc)
    quotes, errors = await fetch_fx_quotes(client)
    if not quotes:
        raise ProviderError("; ".join(errors) or "Sin cotizaciones")
    result = await store_fx_quotes(db, quotes, now)
    result.errors = errors
    await _prune_old_quotes(db, ar_date(now))
    return result


# ── Inflacion ───────────────────────────────────────────────────────────────

MIN_PCT = Decimal("-20")
MAX_PCT = Decimal("100")


def _valid_month(item: InflationIn, current_period: date) -> bool:
    return MIN_PCT <= item.pct <= MAX_PCT and item.period <= current_period


async def fetch_inflation_series(client: httpx.AsyncClient) -> tuple[list[InflationIn], list[str]]:
    errors: list[str] = []
    try:
        series = await argentinadatos.fetch_inflation(client)
        if series:
            return series, errors
        errors.append("ArgentinaDatos inflacion: sin datos")
    except ProviderError as exc:
        logger.warning("Fallo ArgentinaDatos inflacion: %s", exc)
        errors.append(f"ArgentinaDatos inflacion: {exc}")
    try:
        return await datos_gob.fetch_inflation(client), errors
    except ProviderError as exc:
        logger.warning("Fallo datos.gob.ar inflacion: %s", exc)
        errors.append(f"datos.gob.ar: {exc}")
    return [], errors


async def store_inflation(
    db: AsyncSession, series: list[InflationIn], now: datetime, primary: str = argentinadatos.NAME
) -> int:
    repo = MarketRepository(db)
    existing = await repo.inflation_rows()
    current_period = ar_date(now).replace(day=1)
    changed = 0
    for item in series:
        if not _valid_month(item, current_period):
            logger.warning("IPC descartado por sanidad: %s %s", item.period, item.pct)
            continue
        row = existing.get(item.period)
        if row is None:
            db.add(
                InflationMonth(
                    period=item.period, pct=item.pct, provider=item.provider, fetched_at=now
                )
            )
            changed += 1
        elif item.provider == primary and Decimal(str(row.pct)) != item.pct:
            # Revision del INDEC: gana el primario. Un respaldo nunca pisa.
            row.pct = item.pct
            row.provider = item.provider
            row.fetched_at = now
            changed += 1
    await db.commit()
    clear_cache()
    return changed


async def refresh_inflation(
    db: AsyncSession, client: httpx.AsyncClient, now: Optional[datetime] = None
) -> int:
    now = now or datetime.now(timezone.utc)
    series, errors = await fetch_inflation_series(client)
    if not series:
        raise ProviderError("; ".join(errors) or "Sin datos de inflacion")
    return await store_inflation(db, series, now)

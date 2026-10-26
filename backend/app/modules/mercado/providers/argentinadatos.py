"""ArgentinaDatos (https://api.argentinadatos.com, API publica no oficial):
respaldo del dolar (ultimo dia del historico) y fuente primaria del IPC."""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import NamedTuple

import httpx

from app.modules.mercado.providers.base import (
    FxQuoteIn,
    ProviderError,
    get_json,
    parse_decimal,
)

NAME = "argentinadatos"
BASE_URL = "https://api.argentinadatos.com"
#: El historico de la serie arranca en 1943; nos quedamos con lo reciente.
INFLATION_FROM = date(2017, 1, 1)


class InflationIn(NamedTuple):
    period: date
    pct: Decimal
    provider: str


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def parse_latest_fx(payload: object, kind: str) -> list[FxQuoteIn]:
    """Ultimo item del historico diario `[{casa, compra, venta, fecha}]`."""
    if not isinstance(payload, list):
        raise ProviderError("ArgentinaDatos no devolvio una lista de cotizaciones")
    best: tuple[date, dict] | None = None
    for item in payload:
        if not isinstance(item, dict):
            continue
        day = _parse_date(item.get("fecha"))
        if day is None or parse_decimal(item.get("venta")) is None:
            continue
        if best is None or day > best[0]:
            best = (day, item)
    if best is None:
        return []
    day, item = best
    # La fuente publica solo el dia: se toma el mediodia de Argentina (15:00 UTC).
    updated = datetime(day.year, day.month, day.day, 15, 0, tzinfo=timezone.utc)
    return [
        FxQuoteIn(
            currency="USD",
            kind=kind,
            buy=parse_decimal(item.get("compra")),
            sell=parse_decimal(item.get("venta")),
            provider=NAME,
            source_updated_at=updated,
        )
    ]


def parse_inflation(payload: object) -> list[InflationIn]:
    """`[{fecha: "2026-09-30", valor: 1.9}]` -> periodo (dia 1 del mes) + %."""
    if not isinstance(payload, list):
        raise ProviderError("ArgentinaDatos no devolvio una lista de inflacion")
    out: list[InflationIn] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        day = _parse_date(item.get("fecha"))
        pct = parse_decimal(item.get("valor"))
        if day is None or pct is None or day < INFLATION_FROM:
            continue
        out.append(InflationIn(day.replace(day=1), pct, NAME))
    return out


async def fetch_fx(client: httpx.AsyncClient, kind: str) -> list[FxQuoteIn]:
    casa = "bolsa" if kind == "mep" else kind
    return parse_latest_fx(
        await get_json(client, f"{BASE_URL}/v1/cotizaciones/dolares/{casa}"), kind
    )


async def fetch_inflation(client: httpx.AsyncClient) -> list[InflationIn]:
    return parse_inflation(await get_json(client, f"{BASE_URL}/v1/finanzas/indices/inflacion"))

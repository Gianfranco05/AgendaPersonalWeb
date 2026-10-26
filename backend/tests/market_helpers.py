"""Utilidades de los tests de datos de mercado: fixtures grabadas de las APIs
reales, un `httpx.MockTransport` que cuenta los pedidos y atajos para sembrar
la base. Ningun test sale a la red (ver el fixture autouse del conftest)."""

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Optional, Union

import httpx

from app.modules.mercado.models import FxQuote, InflationMonth, MarketFetchState
from app.modules.mercado.repository import ar_date

FIXTURES = Path(__file__).parent / "fixtures" / "market"

DOLARAPI_USD = "dolarapi.com/v1/dolares"
DOLARAPI_EUR = "dolarapi.com/v1/cotizaciones/eur"
BLUELYTICS = "api.bluelytics.com.ar/v2/latest"
AD_PREFIX = "api.argentinadatos.com/v1/cotizaciones/dolares/"
AD_INFLATION = "api.argentinadatos.com/v1/finanzas/indices/inflacion"
DATOS_GOB = "apis.datos.gob.ar/series/api/series/"
COINGECKO = "api.coingecko.com/api/v3/simple/price"


def fixture(name: str):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def default_routes() -> dict:
    """Las respuestas reales grabadas (octubre 2026), por `host/path`."""
    return {
        DOLARAPI_USD: fixture("dolarapi_dolares"),
        DOLARAPI_EUR: fixture("dolarapi_eur"),
        BLUELYTICS: fixture("bluelytics_latest"),
        AD_PREFIX + "bolsa": fixture("argentinadatos_bolsa"),
        AD_PREFIX + "oficial": [
            {"casa": "oficial", "compra": 1500, "venta": 1550, "fecha": "2026-10-23"}
        ],
        AD_PREFIX + "blue": [{"casa": "blue", "compra": 1540, "venta": 1560, "fecha": "2026-10-24"}],
        AD_INFLATION: fixture("argentinadatos_inflacion"),
        DATOS_GOB: fixture("datos_gob_ipc"),
        COINGECKO: fixture("coingecko_simple_price"),
    }


Route = Union[object, Callable[[httpx.Request], httpx.Response], Exception]


class FakeMarket:
    """Servidor falso: `routes[host/path]` puede ser un JSON (200), una
    `Exception` (se levanta, ej. `httpx.ConnectTimeout`), un `int` (status de
    error) o una funcion `request -> Response`."""

    def __init__(self, routes: Optional[dict] = None):
        self.routes = default_routes() if routes is None else dict(routes)
        self.requests: list[httpx.Request] = []

    def calls(self, key: str) -> list[httpx.Request]:
        return [r for r in self.requests if f"{r.url.host}{r.url.path}" == key]

    def count(self, key: Optional[str] = None) -> int:
        return len(self.requests) if key is None else len(self.calls(key))

    def fail(self, *keys: str, error: Optional[Exception] = None) -> None:
        for key in keys:
            self.routes[key] = error or httpx.ConnectTimeout("timeout simulado")

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        key = f"{request.url.host}{request.url.path}"
        route = self.routes.get(key)
        if route is None:
            return httpx.Response(404, json={"error": "sin ruta en el test"})
        if isinstance(route, Exception):
            raise route
        if callable(route):
            return route(request)
        if isinstance(route, int):
            return httpx.Response(route, json={"error": "simulado"})
        return httpx.Response(200, json=route)

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler))

    def factory(self) -> Callable[[], httpx.AsyncClient]:
        return self.client


def at(day: str, hour: int = 12, minute: int = 0) -> datetime:
    y, m, d = (int(x) for x in day.split("-"))
    return datetime(y, m, d, hour, minute, tzinfo=timezone.utc)


async def add_quote(
    db,
    currency: str,
    kind: str,
    sell,
    *,
    buy=None,
    provider: str = "dolarapi",
    as_of: Optional[datetime] = None,
):
    """Siembra una cotizacion directo en la base (sin pasar por los providers)."""
    as_of = as_of or datetime.now(timezone.utc)
    row = FxQuote(
        currency=currency,
        kind=kind,
        quote_date=ar_date(as_of),
        buy=None if buy is None else Decimal(str(buy)),
        sell=Decimal(str(sell)),
        provider=provider,
        source_updated_at=as_of,
        fetched_at=as_of,
    )
    db.add(row)
    await db.commit()
    return row


async def set_state(
    db,
    source: str = "fx",
    *,
    last_success_at: Optional[datetime] = None,
    failures: int = 0,
    next_run_at: Optional[datetime] = None,
):
    row = await db.get(MarketFetchState, source)
    if row is None:
        row = MarketFetchState(
            source=source, next_run_at=next_run_at or datetime(1970, 1, 1, tzinfo=timezone.utc)
        )
        db.add(row)
    row.last_success_at = last_success_at
    row.consecutive_failures = failures
    if next_run_at:
        row.next_run_at = next_run_at
    await db.commit()
    return row


async def add_inflation(db, series: dict[str, float], provider: str = "argentinadatos"):
    """`{"2026-09": 1.9}` -> filas de `inflation_monthly`."""
    now = datetime.now(timezone.utc)
    for key, pct in series.items():
        y, m = (int(x) for x in key.split("-"))
        db.add(
            InflationMonth(
                period=date(y, m, 1), pct=Decimal(str(pct)), provider=provider, fetched_at=now
            )
        )
    await db.commit()


def months_back(count: int, today: Optional[date] = None) -> list[str]:
    """Los `count` meses anteriores al actual, del mas viejo al mas nuevo."""
    today = today or (datetime.now(timezone.utc) - timedelta(hours=3)).date()
    y, m = today.year, today.month
    out = []
    for _ in range(count):
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        out.append(f"{y:04d}-{m:02d}")
    return list(reversed(out))

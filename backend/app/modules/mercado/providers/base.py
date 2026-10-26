"""Base de los providers de datos de mercado: DTOs, cliente HTTP inyectable y
helpers de parseo tolerante (un item invalido se descarta, no tumba la
respuesta entera)."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "Can_cen/1.0"
HTTP_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class ProviderError(Exception):
    """Falla de una fuente externa (red, status != 200, payload ilegible)."""

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


@dataclass(frozen=True)
class FxQuoteIn:
    currency: str
    kind: str
    buy: Optional[Decimal]
    sell: Decimal
    provider: str
    source_updated_at: datetime


def make_client(**kwargs: Any) -> httpx.AsyncClient:
    """Cliente con timeouts cortos y User-Agent propio. Los tests pasan su
    propio cliente (con `httpx.MockTransport`) en vez de usar este."""
    kwargs.setdefault("timeout", HTTP_TIMEOUT)
    headers = {"User-Agent": USER_AGENT, **kwargs.pop("headers", {})}
    return httpx.AsyncClient(headers=headers, **kwargs)


def parse_decimal(value: Any) -> Optional[Decimal]:
    """Decimal finito desde un numero o string JSON; None si no sirve."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def parse_datetime(value: Any) -> Optional[datetime]:
    """ISO-8601 con zona (o sin zona = UTC) a datetime tz-aware en UTC."""
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


async def get_json(client: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
    """GET que devuelve el JSON o levanta `ProviderError` (nunca otra cosa)."""
    try:
        response = await client.get(url, **kwargs)
    except httpx.HTTPError as exc:
        raise ProviderError(f"{type(exc).__name__} consultando {_host(url)}") from exc
    if response.status_code == 429:
        raise ProviderError(f"429 en {_host(url)}", retry_after=_retry_after(response))
    if response.status_code != 200:
        raise ProviderError(f"HTTP {response.status_code} en {_host(url)}")
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderError(f"JSON invalido de {_host(url)}") from exc


def _host(url: str) -> str:
    return httpx.URL(url).host


def _retry_after(response: httpx.Response) -> Optional[float]:
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None


# ── Contrato de los providers de precios de activos ─────────────────────────


@dataclass(frozen=True)
class PriceQuote:
    price: Decimal
    currency: str
    as_of: datetime


class PriceProvider:
    """Un proveedor de precios (CoinGecko, BYMA...). Sumar uno = implementar la
    clase y registrarla en `PRICE_PROVIDERS` (inversiones/valuation.py); el
    esquema no cambia porque el modelo ya guarda `ticker`, `price_source`,
    `last_price` y `last_price_at`."""

    key: str = ""
    supported_types: frozenset[str] = frozenset()

    def supports(self, ticker: str) -> bool:
        raise NotImplementedError

    async def quote_many(
        self, pairs: set[tuple[str, str]], client: httpx.AsyncClient
    ) -> dict[tuple[str, str], PriceQuote]:
        """`pairs` = `{(ticker, moneda del activo)}`. Devuelve lo que pudo
        cotizar, con la misma clave. Levanta `ProviderError` si la fuente falla."""
        raise NotImplementedError

    async def quote(
        self, ticker: str, currency: str, client: httpx.AsyncClient
    ) -> Optional[PriceQuote]:
        return (await self.quote_many({(ticker, currency)}, client)).get((ticker, currency))

"""CoinGecko (https://api.coingecko.com/api/v3): precios de cripto en lote.

Plan Demo gratuito: 10.000 creditos/mes y 100 req/min, con atribucion
obligatoria ("Datos de CoinGecko" en los clientes). La key Demo es opcional y
va por variable de entorno (`COINGECKO_API_KEY`, header `x-cg-demo-api-key`).
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx

from app.config import settings
from app.modules.mercado.crypto_assets import get_asset
from app.modules.mercado.providers.base import (
    PriceProvider,
    PriceQuote,
    ProviderError,
    get_json,
    parse_decimal,
)

NAME = "coingecko"
URL = "https://api.coingecko.com/api/v3/simple/price"
MAX_PRICE = Decimal("1e11")

#: Moneda del activo -> moneda de cotizacion de CoinGecko. USDT se valua 1:1 con USD.
VS_BY_CURRENCY = {"USD": "usd", "USDT": "usd", "ARS": "ars", "EUR": "eur"}


def vs_currency_for(currency: str) -> str:
    """Moneda en la que se guarda/lee el precio en `market_prices`."""
    return "USD" if currency in ("USD", "USDT") else currency


class CoinGeckoProvider(PriceProvider):
    key = NAME
    supported_types = frozenset({"crypto"})

    def supports(self, ticker: str) -> bool:
        return get_asset(ticker) is not None

    async def quote_many(
        self, pairs: set[tuple[str, str]], client: httpx.AsyncClient
    ) -> dict[tuple[str, str], PriceQuote]:
        wanted = [(t, c) for t, c in pairs if get_asset(t) is not None and c in VS_BY_CURRENCY]
        if not wanted:
            return {}
        ids = sorted({get_asset(t).coingecko_id for t, _ in wanted})
        vs = sorted({VS_BY_CURRENCY[c] for _, c in wanted})
        headers = {"Accept": "application/json"}
        if settings.COINGECKO_API_KEY:
            headers["x-cg-demo-api-key"] = settings.COINGECKO_API_KEY
        payload = await get_json(
            client,
            URL,
            params={
                "ids": ",".join(ids),
                "vs_currencies": ",".join(vs),
                "include_last_updated_at": "true",
            },
            headers=headers,
        )
        if not isinstance(payload, dict):
            raise ProviderError("CoinGecko no devolvio un objeto")

        now = datetime.now(timezone.utc)
        out: dict[tuple[str, str], PriceQuote] = {}
        for ticker, currency in wanted:
            entry = payload.get(get_asset(ticker).coingecko_id)
            if not isinstance(entry, dict):
                continue
            price = parse_decimal(entry.get(VS_BY_CURRENCY[currency]))
            if price is None or not (Decimal(0) < price <= MAX_PRICE):
                continue
            out[(ticker, currency)] = PriceQuote(price, currency, _as_of(entry, now))
        return out


def _as_of(entry: dict, fallback: datetime) -> datetime:
    raw = entry.get("last_updated_at")
    if isinstance(raw, (int, float)) and not isinstance(raw, bool) and raw > 0:
        try:
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return fallback
    return fallback

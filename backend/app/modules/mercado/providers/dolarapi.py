"""DolarAPI (https://dolarapi.com): una sola respuesta con todos los tipos de
dolar, y el euro oficial aparte."""

import httpx

from app.modules.mercado.providers.base import (
    FxQuoteIn,
    ProviderError,
    get_json,
    parse_datetime,
    parse_decimal,
)

NAME = "dolarapi"
BASE_URL = "https://dolarapi.com"

#: Nombre de DolarAPI -> tipo normalizado.
KIND_BY_CASA = {
    "oficial": "oficial",
    "bolsa": "mep",
    "blue": "blue",
    "contadoconliqui": "ccl",
    "mayorista": "mayorista",
    "cripto": "cripto",
    "tarjeta": "tarjeta",
}


def _parse_item(item: object, currency: str, kind: str) -> FxQuoteIn | None:
    if not isinstance(item, dict):
        return None
    sell = parse_decimal(item.get("venta"))
    updated = parse_datetime(item.get("fechaActualizacion"))
    if sell is None or updated is None:
        return None
    return FxQuoteIn(
        currency=currency,
        kind=kind,
        buy=parse_decimal(item.get("compra")),
        sell=sell,
        provider=NAME,
        source_updated_at=updated,
    )


def parse_dolares(payload: object) -> list[FxQuoteIn]:
    if not isinstance(payload, list):
        raise ProviderError("DolarAPI /v1/dolares no devolvio una lista")
    quotes: list[FxQuoteIn] = []
    for item in payload:
        casa = item.get("casa") if isinstance(item, dict) else None
        kind = KIND_BY_CASA.get(casa) if isinstance(casa, str) else None
        if kind is None:
            continue
        quote = _parse_item(item, "USD", kind)
        if quote is not None:
            quotes.append(quote)
    return quotes


def parse_eur(payload: object) -> list[FxQuoteIn]:
    quote = _parse_item(payload, "EUR", "oficial")
    return [quote] if quote is not None else []


async def fetch_usd(client: httpx.AsyncClient) -> list[FxQuoteIn]:
    return parse_dolares(await get_json(client, f"{BASE_URL}/v1/dolares"))


async def fetch_eur(client: httpx.AsyncClient) -> list[FxQuoteIn]:
    return parse_eur(await get_json(client, f"{BASE_URL}/v1/cotizaciones/eur"))

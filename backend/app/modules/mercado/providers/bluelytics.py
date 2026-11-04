"""Bluelytics (https://api.bluelytics.com.ar): respaldo para oficial y blue
(USD y EUR). No tiene MEP."""

import httpx

from app.modules.mercado.providers.base import (
    FxQuoteIn,
    ProviderError,
    get_json,
    parse_datetime,
    parse_decimal,
)

NAME = "bluelytics"
URL = "https://api.bluelytics.com.ar/v2/latest"

#: clave del payload -> (moneda, tipo)
KEYS = {
    "oficial": ("USD", "oficial"),
    "blue": ("USD", "blue"),
    "oficial_euro": ("EUR", "oficial"),
    "blue_euro": ("EUR", "blue"),
}


def parse_latest(payload: object) -> list[FxQuoteIn]:
    if not isinstance(payload, dict):
        raise ProviderError("Bluelytics no devolvio un objeto")
    # Bluelytics trae un solo timestamp para todo el payload.
    updated = parse_datetime(payload.get("last_update"))
    if updated is None:
        return []
    quotes: list[FxQuoteIn] = []
    for key, (currency, kind) in KEYS.items():
        item = payload.get(key)
        if not isinstance(item, dict):
            continue
        sell = parse_decimal(item.get("value_sell"))
        if sell is None:
            continue
        quotes.append(
            FxQuoteIn(
                currency=currency,
                kind=kind,
                buy=parse_decimal(item.get("value_buy")),
                sell=sell,
                provider=NAME,
                source_updated_at=updated,
            )
        )
    return quotes


async def fetch(client: httpx.AsyncClient) -> list[FxQuoteIn]:
    return parse_latest(await get_json(client, URL))

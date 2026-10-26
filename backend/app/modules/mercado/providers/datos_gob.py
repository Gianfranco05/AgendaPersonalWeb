"""API de Series de Tiempo de datos.gob.ar (INDEC): respaldo oficial del IPC.
Serie nacional, nivel mensual base dic-2016; con `percent_change` devuelve la
variacion mensual como fraccion (0.0166 = 1,66 %)."""

from datetime import date
from decimal import Decimal

import httpx

from app.modules.mercado.providers.argentinadatos import INFLATION_FROM, InflationIn
from app.modules.mercado.providers.base import ProviderError, get_json, parse_decimal

NAME = "datos_gob"
URL = "https://apis.datos.gob.ar/series/api/series/"
SERIES_ID = "148.3_INIVELNAL_DICI_M_26"


def parse_series(payload: object) -> list[InflationIn]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ProviderError("datos.gob.ar no devolvio una serie")
    out: list[InflationIn] = []
    for row in payload["data"]:
        if not isinstance(row, list) or len(row) < 2 or not isinstance(row[0], str):
            continue
        try:
            period = date.fromisoformat(row[0][:10]).replace(day=1)
        except ValueError:
            continue
        fraction = parse_decimal(row[1])
        if fraction is None or period < INFLATION_FROM:
            continue
        pct = (fraction * Decimal(100)).quantize(Decimal("0.0001"))
        out.append(InflationIn(period, pct, NAME))
    return out


async def fetch_inflation(client: httpx.AsyncClient) -> list[InflationIn]:
    params = {
        "ids": SERIES_ID,
        "representation_mode": "percent_change",
        "format": "json",
        "start_date": INFLATION_FROM.isoformat(),
        "limit": "1000",
    }
    return parse_series(await get_json(client, URL, params=params))

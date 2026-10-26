"""Cotizacion efectiva del usuario: que dolar/euro usa para convertir.

Resolucion (D4): `manual` -> la cotizacion propia; automatica -> la `sell` de
la ultima cotizacion guardada de ese tipo (aunque el ultimo intento haya
fallado: la tabla nunca se vacia por un error); automatica sin ninguna fila
guardada -> la manual del usuario como `manual_fallback`, y si tampoco hay,
sin cotizacion.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from app.modules.mercado.repository import FxSnapshot, as_utc

USD_SOURCES = ("oficial", "mep", "blue", "manual")
EUR_SOURCES = ("oficial", "blue", "manual")

#: Oficial y MEP no cotizan los fines de semana: 96 h cubre un finde largo.
STALE_AFTER = timedelta(hours=96)
#: Si el job `fx` no tuvo exito en este tiempo, lo automatico se marca desactualizado.
FETCH_STALE_AFTER = timedelta(hours=6)

KIND_LABELS = {
    "oficial": "Oficial",
    "mep": "MEP",
    "blue": "Blue",
    "ccl": "CCL",
    "mayorista": "Mayorista",
    "cripto": "Cripto",
    "tarjeta": "Tarjeta",
}


@dataclass(frozen=True)
class RateInfo:
    #: Fuente pedida por el usuario (oficial | mep | blue | manual).
    source: str
    #: La que realmente se uso: el tipo, `manual`, `manual_fallback` o None.
    effective_source: Optional[str] = None
    rate: Optional[Decimal] = None
    buy: Optional[Decimal] = None
    provider: Optional[str] = None
    as_of: Optional[datetime] = None
    stale: bool = False


def fetch_is_stale(snapshot: FxSnapshot, now: datetime) -> bool:
    state = snapshot.state
    if state is None or state.last_success_at is None:
        return False
    return now - state.last_success_at > FETCH_STALE_AFTER


def resolve_rate(
    currency: str,
    source: str,
    manual_rate: Optional[Decimal],
    manual_as_of: Optional[datetime],
    snapshot: FxSnapshot,
    now: Optional[datetime] = None,
) -> RateInfo:
    now = now or datetime.now(timezone.utc)
    if source == "manual":
        if manual_rate is None:
            return RateInfo(source="manual")
        return RateInfo(
            source="manual",
            effective_source="manual",
            rate=manual_rate,
            as_of=as_utc(manual_as_of),
        )
    quote = snapshot.quotes.get((currency, source))
    if quote is None:
        if manual_rate is not None:
            return RateInfo(
                source=source,
                effective_source="manual_fallback",
                rate=manual_rate,
                as_of=as_utc(manual_as_of),
            )
        return RateInfo(source=source)
    stale = now - quote.as_of > STALE_AFTER or fetch_is_stale(snapshot, now)
    return RateInfo(
        source=source,
        effective_source=quote.kind,
        rate=quote.sell,
        buy=quote.buy,
        provider=quote.provider,
        as_of=quote.as_of,
        stale=stale,
    )

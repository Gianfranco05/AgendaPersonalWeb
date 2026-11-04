"""Scheduler de datos de mercado (dolar, IPC, cripto).

Corre en el `lifespan` de cada worker de gunicorn, pero las fuentes externas
se consultan UNA vez por ciclo en total, no una por worker: cada fuente tiene
una fila en `market_fetch_state` y quien consulta antes toma un *lease*
atomico (`UPDATE ... WHERE next_run_at <= now AND lease_until vencido`, gana
el que ve `rowcount == 1`). No depende de Redis, sobrevive reinicios y un
worker que muere con el lease lo libera solo al vencer.

El lease se commitea ANTES de salir a la red (ninguna transaccion abierta
durante las llamadas HTTP). Al terminar: exito -> proximo ciclo en el
intervalo; error -> backoff exponencial con tope. Ninguna excepcion sale del
loop, igual que los otros schedulers.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Optional

import httpx

from app.config import settings
from app.database import AsyncSessionLocal
from app.modules.mercado.providers.base import ProviderError, make_client
from app.modules.mercado.repository import MarketRepository
from app.modules.mercado.service import ensure_state_rows, refresh_fx, refresh_inflation

logger = logging.getLogger(__name__)

CYCLE_SECONDS = 60
LEASE_SECONDS = 120
HOUR = 3600


async def _refresh_crypto(db, client: httpx.AsyncClient, now: datetime) -> None:
    from app.modules.inversiones.valuation import refresh_quotes

    await refresh_quotes(db, client)


Job = Callable[..., Awaitable[object]]
JOBS: dict[str, Job] = {
    "fx": refresh_fx,
    "inflation": refresh_inflation,
    "crypto": _refresh_crypto,
}


def interval_seconds(source: str) -> float:
    if source == "fx":
        return max(1, settings.MARKET_FX_REFRESH_MINUTES) * 60
    if source == "crypto":
        return max(1, settings.MARKET_CRYPTO_REFRESH_MINUTES) * 60
    return max(1, settings.MARKET_INFLATION_REFRESH_HOURS) * HOUR


def backoff_cap_seconds(source: str) -> float:
    """Tope del backoff: 1 h para dolar/cripto, 24 h para el IPC."""
    return 24 * HOUR if source == "inflation" else HOUR


def next_delay_seconds(source: str, failures: int, retry_after: Optional[float] = None) -> float:
    """Segundos hasta el proximo intento: intervalo x 2^fallos, con tope."""
    base = interval_seconds(source)
    if failures <= 0:
        delay = base
    else:
        delay = min(base * (2**failures), max(backoff_cap_seconds(source), base))
    if retry_after:
        delay = max(delay, retry_after)
    return delay


def enabled_sources() -> list[str]:
    sources = ["fx", "inflation"]
    if settings.MARKET_CRYPTO_ENABLED:
        sources.append("crypto")
    return sources


async def run_source(
    source: str,
    session_factory,
    client_factory: Callable[[], httpx.AsyncClient],
    now: datetime,
) -> bool:
    """Intenta tomar el lease de `source` y, si lo logra, corre el job.
    Devuelve True si esta llamada fue la que consulto."""
    async with session_factory() as db:
        repo = MarketRepository(db)
        if not await repo.try_acquire_lease(source, now, LEASE_SECONDS):
            return False
        state = await repo.fetch_state(source)
        previous_failures = state.consecutive_failures if state else 0
        # Fin de la transaccion de lectura: la red va sin transaccion abierta.
        await db.commit()
        try:
            async with client_factory() as client:
                await JOBS[source](db, client, now)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await db.rollback()
            retry_after = exc.retry_after if isinstance(exc, ProviderError) else None
            delay = next_delay_seconds(source, previous_failures + 1, retry_after)
            logger.warning("Fallo la consulta de %s: %s", source, exc)
            await repo.finish(
                source,
                now=now,
                next_run_at=now + timedelta(seconds=delay),
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )
        else:
            await repo.finish(
                source,
                now=now,
                next_run_at=now + timedelta(seconds=next_delay_seconds(source, 0)),
                success=True,
            )
    return True


async def _tick(
    now: Optional[datetime] = None,
    session_factory=AsyncSessionLocal,
    client_factory: Callable[[], httpx.AsyncClient] = make_client,
) -> list[str]:
    """Un ciclo: devuelve las fuentes que consulto esta llamada."""
    now = now or datetime.now(timezone.utc)
    async with session_factory() as db:
        await ensure_state_rows(db)
    ran = []
    for source in enabled_sources():
        try:
            if await run_source(source, session_factory, client_factory, now):
                ran.append(source)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Fallo el ciclo de datos de mercado para %s", source)
    return ran


async def run_market_data_scheduler() -> None:
    """Loop de fondo arrancado desde el lifespan. Un ciclo fallido (DB caida un
    instante) se loguea y el loop sigue."""
    logger.info("Scheduler de datos de mercado iniciado")
    while True:
        try:
            await _tick()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Fallo un ciclo del scheduler de datos de mercado")
        await asyncio.sleep(CYCLE_SECONDS)

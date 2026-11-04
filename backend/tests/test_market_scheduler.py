"""Scheduler de datos de mercado: lease entre workers, backoff, estado inicial,
resiliencia y kill switch."""

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.main import app, lifespan
from app.modules.mercado import scheduler
from app.modules.mercado.models import FxQuote, InflationMonth, MarketFetchState
from app.modules.mercado.repository import MarketRepository
from app.modules.mercado.service import ensure_state_rows
from market_helpers import AD_INFLATION, DOLARAPI_EUR, DOLARAPI_USD, FakeMarket, at

pytestmark = pytest.mark.asyncio

NOW = at("2026-10-26", 15)


@pytest_asyncio.fixture
async def file_maker(tmp_path):
    """SQLite en archivo: cada sesion tiene SU conexion, como los workers de
    gunicorn (el engine de los tests comparte una sola conexion)."""
    from app.core.base import Base

    file_engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'workers.db'}")
    async with file_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(file_engine, class_=AsyncSession, expire_on_commit=False)
    await file_engine.dispose()


@pytest.fixture
def maker(engine):
    """Una sesion NUEVA por 'worker', como en produccion (cada worker de
    gunicorn tiene la suya)."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def state(maker, source):
    async with maker() as db:
        row = await db.get(MarketFetchState, source)
        await db.refresh(row)
        return row


def utc(value):
    return value.replace(tzinfo=timezone.utc)


# ── Estado inicial ──────────────────────────────────────────────────────────


async def test_ensure_state_rows_crea_las_filas_que_faltan(maker):
    async with maker() as db:
        await ensure_state_rows(db)
        await ensure_state_rows(db)  # idempotente
        rows = (await db.execute(select(MarketFetchState.source))).scalars().all()
    assert sorted(rows) == ["crypto", "fx", "inflation"]


async def test_primer_ciclo_corre_todo_y_guarda_datos(maker):
    fake = FakeMarket()
    ran = await scheduler._tick(NOW, maker, fake.factory())
    assert ran == ["fx", "inflation", "crypto"]
    async with maker() as db:
        assert (await db.execute(select(FxQuote))).scalars().first() is not None
        assert (await db.execute(select(InflationMonth))).scalars().first() is not None
    for source in ("fx", "inflation", "crypto"):
        row = await state(maker, source)
        assert utc(row.last_success_at) == NOW and row.consecutive_failures == 0
        assert row.lease_until is None
    # Sin cripto en uso no hubo pedido a CoinGecko.
    assert fake.count("api.coingecko.com/api/v3/simple/price") == 0
    assert utc((await state(maker, "fx")).next_run_at) == NOW + timedelta(minutes=15)
    assert utc((await state(maker, "crypto")).next_run_at) == NOW + timedelta(minutes=10)
    assert utc((await state(maker, "inflation")).next_run_at) == NOW + timedelta(hours=6)


async def test_no_vuelve_a_consultar_antes_de_tiempo(maker):
    fake = FakeMarket()
    await scheduler._tick(NOW, maker, fake.factory())
    before = fake.count()
    # A los 5 min ninguna fuente esta vencida: no hay un solo pedido.
    assert await scheduler._tick(NOW + timedelta(minutes=5), maker, fake.factory()) == []
    assert fake.count() == before
    assert await scheduler._tick(NOW + timedelta(minutes=16), maker, fake.factory()) == ["fx", "crypto"]
    assert fake.count(DOLARAPI_USD) == 2 and fake.count(AD_INFLATION) == 1


# ── Lease entre workers ─────────────────────────────────────────────────────


async def test_tres_workers_a_la_vez_solo_uno_consulta(file_maker):
    async with file_maker() as db:
        await ensure_state_rows(db)
    fake = FakeMarket()
    results = await asyncio.gather(
        *[scheduler.run_source("fx", file_maker, fake.factory(), NOW) for _ in range(3)]
    )
    assert sorted(results) == [False, False, True]
    assert fake.count(DOLARAPI_USD) == 1 and fake.count(DOLARAPI_EUR) == 1


async def test_tres_workers_con_ciclo_completo(file_maker):
    """Incluye la carrera por crear las filas de estado: ninguna explota."""
    fake = FakeMarket()
    ran = await asyncio.gather(*[scheduler._tick(NOW, file_maker, fake.factory()) for _ in range(3)])
    flat = [s for worker in ran for s in worker]
    assert sorted(flat) == ["crypto", "fx", "inflation"]  # cada fuente la corrio uno solo
    assert fake.count(DOLARAPI_USD) == 1 and fake.count(AD_INFLATION) == 1


async def test_lease_vigente_bloquea_y_vencido_se_retoma(maker):
    async with maker() as db:
        await ensure_state_rows(db)
        row = await db.get(MarketFetchState, "fx")
        row.lease_until = NOW + timedelta(seconds=100)  # otro worker lo tiene
        await db.commit()
    fake = FakeMarket()
    assert await scheduler.run_source("fx", maker, fake.factory(), NOW) is False
    assert fake.count() == 0
    # El worker murio: 120 s despues el lease esta vencido.
    assert await scheduler.run_source("fx", maker, fake.factory(), NOW + timedelta(seconds=101)) is True
    assert fake.count(DOLARAPI_USD) == 1


async def test_lease_se_commitea_antes_de_la_red(maker):
    """Mientras el job esta en la red, otra sesion ya ve el lease tomado."""
    observed = {}
    fake = FakeMarket()

    async def probe(request):
        async with maker() as other:
            row = await other.get(MarketFetchState, "fx")
            observed["lease"] = row.lease_until
        return fake.handler(request)

    def handler(request):  # MockTransport admite handlers async
        return probe(request)

    async with maker() as db:
        await ensure_state_rows(db)
    client_factory = lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))  # noqa: E731
    assert await scheduler.run_source("fx", maker, client_factory, NOW) is True
    assert observed["lease"] is not None
    assert utc(observed["lease"]) == NOW + timedelta(seconds=scheduler.LEASE_SECONDS)


# ── Backoff y errores ───────────────────────────────────────────────────────


async def test_backoff_exponencial_con_tope(maker):
    fake = FakeMarket({})  # todas las fuentes responden 404
    async with maker() as db:
        await ensure_state_rows(db)
    t = NOW
    expected = [30, 60, 60]
    for failures, minutes in enumerate(expected, start=1):
        assert await scheduler.run_source("fx", maker, fake.factory(), t) is True
        row = await state(maker, "fx")
        assert row.consecutive_failures == failures
        assert utc(row.next_run_at) == t + timedelta(minutes=minutes)
        assert row.last_error and len(row.last_error) <= 300
        assert row.lease_until is None
        t = t + timedelta(minutes=minutes)


async def test_backoff_de_inflacion_con_tope_de_24h():
    assert scheduler.next_delay_seconds("inflation", 1) == 12 * 3600
    assert scheduler.next_delay_seconds("inflation", 2) == 24 * 3600
    assert scheduler.next_delay_seconds("inflation", 6) == 24 * 3600
    assert scheduler.next_delay_seconds("fx", 0) == 15 * 60
    assert scheduler.next_delay_seconds("fx", 9) == 3600
    assert scheduler.next_delay_seconds("crypto", 1, retry_after=7200) == 7200


async def test_exito_despues_de_fallos_resetea_el_contador(maker):
    async with maker() as db:
        await ensure_state_rows(db)
    broken = FakeMarket({})
    await scheduler.run_source("fx", maker, broken.factory(), NOW)
    assert (await state(maker, "fx")).consecutive_failures == 1
    ok = FakeMarket()
    later = NOW + timedelta(minutes=31)
    await scheduler.run_source("fx", maker, ok.factory(), later)
    row = await state(maker, "fx")
    assert row.consecutive_failures == 0 and row.last_error is None
    assert utc(row.last_success_at) == later


async def test_excepcion_inesperada_de_un_provider_no_corta_el_ciclo(maker, monkeypatch):
    async def boom(db, client, now):
        raise RuntimeError("bug en el provider")

    monkeypatch.setitem(scheduler.JOBS, "fx", boom)
    fake = FakeMarket()
    ran = await scheduler._tick(NOW, maker, fake.factory())
    assert ran == ["fx", "inflation", "crypto"]  # siguio con las demas
    row = await state(maker, "fx")
    assert row.consecutive_failures == 1 and "RuntimeError" in row.last_error
    assert (await state(maker, "inflation")).last_success_at is not None


async def test_falla_de_red_en_el_dolar_no_afecta_a_la_inflacion(maker):
    fake = FakeMarket()
    fake.fail(DOLARAPI_USD, DOLARAPI_EUR)
    fake.routes["api.bluelytics.com.ar/v2/latest"] = 500
    fake.routes["api.argentinadatos.com/v1/cotizaciones/dolares/oficial"] = 500
    fake.routes["api.argentinadatos.com/v1/cotizaciones/dolares/bolsa"] = 500
    fake.routes["api.argentinadatos.com/v1/cotizaciones/dolares/blue"] = 500
    await scheduler._tick(NOW, maker, fake.factory())
    assert (await state(maker, "fx")).consecutive_failures == 1
    assert (await state(maker, "inflation")).consecutive_failures == 0


# ── Lifespan / kill switch / tiempos ────────────────────────────────────────


async def test_el_scheduler_no_arranca_con_market_data_apagado(monkeypatch):
    started = []

    async def fake_loop():
        started.append(True)
        await asyncio.sleep(3600)

    monkeypatch.setattr("app.main.run_market_data_scheduler", fake_loop)
    monkeypatch.setattr("app.main.run_reminder_scheduler", lambda: asyncio.sleep(3600))
    monkeypatch.setattr("app.main.run_investment_alert_scheduler", lambda: asyncio.sleep(3600))

    monkeypatch.setattr(settings, "MARKET_DATA_ENABLED", False)
    async with lifespan(app):
        await asyncio.sleep(0)
    assert started == []

    monkeypatch.setattr(settings, "MARKET_DATA_ENABLED", True)
    async with lifespan(app):
        await asyncio.sleep(0)
    assert started == [True]


def test_el_entorno_de_tests_tiene_market_data_apagado():
    assert settings.MARKET_DATA_ENABLED is False


def test_cliente_http_con_timeouts_y_user_agent():
    from app.modules.mercado.providers.base import make_client

    client = make_client()
    assert client.timeout == httpx.Timeout(10.0, connect=5.0)
    assert client.headers["user-agent"] == "Can_cen/1.0"


async def test_intervalos_configurables(monkeypatch):
    monkeypatch.setattr(settings, "MARKET_FX_REFRESH_MINUTES", 5)
    monkeypatch.setattr(settings, "MARKET_INFLATION_REFRESH_HOURS", 1)
    assert scheduler.interval_seconds("fx") == 300
    assert scheduler.interval_seconds("inflation") == 3600


async def test_el_guardia_de_red_real_falla_el_test():
    """Un cliente con transporte real NO sale a internet en los tests."""
    async with httpx.AsyncClient() as client:
        with pytest.raises(AssertionError, match="llamada de red real"):
            await client.get("https://dolarapi.com/v1/dolares")


async def test_repository_lease_directo(maker):
    async with maker() as db:
        await ensure_state_rows(db)
    async with maker() as a, maker() as b:
        first = await MarketRepository(a).try_acquire_lease("crypto", NOW, 120)
        second = await MarketRepository(b).try_acquire_lease("crypto", NOW, 120)
    assert (first, second) == (True, False)

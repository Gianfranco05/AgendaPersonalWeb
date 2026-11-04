"""Cripto automatica con CoinGecko: lote unico, validaciones, cache de precios,
valuacion, frescura y la guarda de que no hay pedidos sin activos."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select

from app.config import settings
from app.modules.inversiones.models import Investment
from app.modules.inversiones.valuation import refresh_quotes
from app.modules.mercado import scheduler
from app.modules.mercado.models import MarketFetchState, MarketPrice
from app.modules.mercado.providers.base import ProviderError
from app.modules.mercado.providers.coingecko import CoinGeckoProvider
from market_helpers import COINGECKO, FakeMarket, fixture, set_state

pytestmark = pytest.mark.asyncio

INVEST = "/api/v1/finance/investments"
NOW = datetime.now(timezone.utc)


def D(value) -> Decimal:
    return Decimal(str(value))


def btc(**overrides):
    body = {
        "asset_type": "crypto",
        "name": "Bitcoin",
        "ticker": "btc",
        "currency": "USD",
        "quantity": "0.5",
        "invested_amount": "30000",
        "price_source": "coingecko",
    }
    body.update(overrides)
    return body


async def add_price(db, symbol, vs, price, *, age_minutes=1):
    stamp = NOW - timedelta(minutes=age_minutes)
    db.add(
        MarketPrice(
            provider="coingecko",
            symbol=symbol,
            vs_currency=vs,
            price=D(price),
            source_updated_at=stamp,
            fetched_at=stamp,
        )
    )
    await db.commit()


# ── Provider ────────────────────────────────────────────────────────────────


def test_tickers_soportados():
    provider = CoinGeckoProvider()
    for ticker in ("BTC", "ETH", "USDT", "USDC", "DAI", "SOL", "BNB", "XRP", "ADA", "DOGE"):
        assert provider.supports(ticker)
    assert not provider.supports("FOOCOIN") and not provider.supports("")


async def test_quote_many_una_sola_consulta_con_moneda_por_activo():
    fake = FakeMarket()
    fake.routes[COINGECKO] = {
        "bitcoin": {"usd": 79632, "ars": 121065474, "last_updated_at": 1792984990},
        "ethereum": {"usd": 2500.5, "ars": 3800000, "eur": 2300, "last_updated_at": 1792984990},
    }
    pairs = {("BTC", "USD"), ("BTC", "USDT"), ("ETH", "ARS"), ("ETH", "EUR"), ("FOO", "USD")}
    async with fake.client() as client:
        quotes = await CoinGeckoProvider().quote_many(pairs, client)

    assert fake.count(COINGECKO) == 1
    params = fake.calls(COINGECKO)[0].url.params
    assert params["ids"] == "bitcoin,ethereum"
    assert set(params["vs_currencies"].split(",")) == {"usd", "ars", "eur"}
    assert params["include_last_updated_at"] == "true"
    assert quotes[("BTC", "USD")].price == D("79632")
    assert quotes[("BTC", "USDT")].price == D("79632")  # USDT se valua como USD
    assert quotes[("ETH", "ARS")].price == D("3800000")
    assert quotes[("ETH", "EUR")].price == D("2300")
    assert ("FOO", "USD") not in quotes
    assert quotes[("BTC", "USD")].as_of == datetime.fromtimestamp(1792984990, tz=timezone.utc)


async def test_payload_real_grabado():
    fake = FakeMarket()
    async with fake.client() as client:
        quotes = await CoinGeckoProvider().quote_many({("USDT", "ARS"), ("BTC", "USD")}, client)
    assert quotes[("BTC", "USD")].price == D("79632")
    assert quotes[("USDT", "ARS")].price == D("1518.68")


@pytest.mark.parametrize("bad", [0, -5, 2e11, "x", None])
async def test_precios_fuera_de_rango_se_descartan(bad):
    fake = FakeMarket()
    fake.routes[COINGECKO] = {"bitcoin": {"usd": bad}, "tether": {"usd": 1}}
    async with fake.client() as client:
        quotes = await CoinGeckoProvider().quote_many({("BTC", "USD"), ("USDT", "USD")}, client)
    assert ("BTC", "USD") not in quotes and quotes[("USDT", "USD")].price == D("1")


async def test_header_de_api_key_solo_si_hay_key(monkeypatch):
    fake = FakeMarket()
    monkeypatch.setattr(settings, "COINGECKO_API_KEY", "")
    async with fake.client() as client:
        await CoinGeckoProvider().quote_many({("BTC", "USD")}, client)
    assert "x-cg-demo-api-key" not in fake.calls(COINGECKO)[0].headers

    monkeypatch.setattr(settings, "COINGECKO_API_KEY", "CG-clave-de-prueba")
    async with fake.client() as client:
        await CoinGeckoProvider().quote_many({("BTC", "USD")}, client)
    assert fake.calls(COINGECKO)[1].headers["x-cg-demo-api-key"] == "CG-clave-de-prueba"


async def test_429_levanta_error_con_retry_after():
    fake = FakeMarket()
    fake.routes[COINGECKO] = lambda req: httpx.Response(429, headers={"Retry-After": "120"})
    async with fake.client() as client:
        with pytest.raises(ProviderError) as exc:
            await CoinGeckoProvider().quote_many({("BTC", "USD")}, client)
    assert exc.value.retry_after == 120


# ── refresh_quotes (job global) ─────────────────────────────────────────────


async def test_un_solo_pedido_para_varios_usuarios_y_monedas(api_auth_client, db_session, test_user):
    from app.modules.auth.models import User
    from app.core.security import hash_password

    other = User(
        id="b1b2b3b4-e5f6-7890-abcd-ef1234567891",
        email="otro@test.com",
        password_hash=hash_password("x"),
        full_name="Otro",
        is_active=True,
        is_verified=True,
    )
    db_session.add(other)
    await db_session.commit()
    await api_auth_client.post(INVEST, json=btc())
    for body in (
        dict(user_id=other.id, name="BTC otro", ticker="BTC", currency="USD", quantity=D("1")),
        dict(user_id=other.id, name="ETH otro", ticker="ETH", currency="ARS", quantity=D("2")),
    ):
        db_session.add(
            Investment(
                asset_type="crypto",
                invested_amount=D("1000"),
                price_source="coingecko",
                status="active",
                notify_maturity=True,
                **body,
            )
        )
    await db_session.commit()

    fake = FakeMarket()
    fake.routes[COINGECKO] = {
        "bitcoin": {"usd": 80000, "last_updated_at": 1792984990},
        "ethereum": {"ars": 3800000, "last_updated_at": 1792984990},
    }
    async with fake.client() as client:
        updated = await refresh_quotes(db_session, client)

    assert fake.count() == 1
    params = fake.calls(COINGECKO)[0].url.params
    assert params["ids"] == "bitcoin,ethereum"
    assert set(params["vs_currencies"].split(",")) == {"usd", "ars"}
    assert updated == 3
    rows = (await db_session.execute(select(Investment))).scalars().all()
    assert {r.name: D(r.last_price) for r in rows} == {
        "Bitcoin": D("80000"),
        "BTC otro": D("80000"),
        "ETH otro": D("3800000"),
    }
    prices = {
        (p.symbol, p.vs_currency): D(p.price)
        for p in (await db_session.execute(select(MarketPrice))).scalars()
    }
    assert prices == {("BTC", "USD"): D("80000"), ("ETH", "ARS"): D("3800000")}


async def test_sin_cripto_en_uso_no_hay_pedido(db_session):
    fake = FakeMarket()
    async with fake.client() as client:
        assert await refresh_quotes(db_session, client) == 0
    assert fake.count() == 0


async def test_activos_cerrados_o_manuales_no_se_consultan(api_auth_client, db_session):
    created = (await api_auth_client.post(INVEST, json=btc())).json()
    await api_auth_client.put(f"{INVEST}/{created['id']}", json={"status": "closed"})
    await api_auth_client.post(INVEST, json=btc(price_source="manual", name="Manual"))
    fake = FakeMarket()
    async with fake.client() as client:
        assert await refresh_quotes(db_session, client) == 0
    assert fake.count() == 0


async def test_job_429_pospone_el_proximo_intento(api_auth_client, db_session):
    created = (await api_auth_client.post(INVEST, json=btc())).json()
    await api_auth_client.put(f"{INVEST}/{created['id']}", json={})  # sin cambios
    fake = FakeMarket()
    fake.routes[COINGECKO] = lambda req: httpx.Response(429, headers={"Retry-After": "7200"})

    now = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
    await set_state(db_session, "crypto", next_run_at=now - timedelta(minutes=1))
    maker = lambda: _SessionCtx(db_session)  # noqa: E731
    await scheduler.run_source("crypto", maker, fake.factory(), now)

    state = await db_session.get(MarketFetchState, "crypto")
    await db_session.refresh(state)
    assert state.consecutive_failures == 1
    next_run = state.next_run_at.replace(tzinfo=timezone.utc)
    assert next_run - now >= timedelta(seconds=7200)  # respeta Retry-After
    inv = (await db_session.execute(select(Investment))).scalars().one()
    assert inv.last_price is None  # conserva lo que tenia


class _SessionCtx:
    """`async with` sobre la sesion compartida del test (sin cerrarla)."""

    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *exc):
        return False


# ── Alta / edicion de activos automaticos ───────────────────────────────────


async def test_crear_btc_con_precio_en_cache(api_auth_client, db_session):
    await add_price(db_session, "BTC", "USD", "79509")
    resp = await api_auth_client.post(INVEST, json=btc())
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert D(data["last_price"]) == D("79509") and data["last_price_at"] is not None
    assert D(data["effective_value"]) == D("39754.50") and data["value_source"] == "quote"
    assert data["quote_provider"] == "CoinGecko" and data["quote_stale"] is False
    assert data["ticker"] == "BTC" and data["price_source"] == "coingecko"


async def test_sin_precio_en_cache_agenda_el_job_y_valua_sin_cotizacion(api_auth_client, db_session):
    resp = await api_auth_client.post(INVEST, json=btc(ticker="ETH", currency="EUR", quantity="2"))
    assert resp.status_code == 201
    data = resp.json()
    assert data["last_price"] is None and data["value_source"] == "invested"
    assert data["quote_provider"] == "CoinGecko" and data["quote_stale"] is None
    state = await db_session.get(MarketFetchState, "crypto")
    assert state is not None
    assert state.next_run_at.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc)


async def test_la_moneda_USDT_usa_el_precio_en_usd(api_auth_client, db_session):
    await add_price(db_session, "ETH", "USD", "2500")
    data = (await api_auth_client.post(INVEST, json=btc(ticker="ETH", currency="USDT", quantity="2"))).json()
    assert D(data["effective_value"]) == D("5000.00")


@pytest.mark.parametrize(
    "overrides",
    [
        {"ticker": "FOOCOIN"},
        {"ticker": None},
        {"quantity": None},
        {"quantity": "0"},
        {"asset_type": "stock"},
        {"asset_type": "bond"},
        {"asset_type": "fund"},
        {"price_source": "binance"},
    ],
)
async def test_validaciones_del_alta_son_422(api_auth_client, overrides):
    resp = await api_auth_client.post(INVEST, json=btc(**overrides))
    assert resp.status_code == 422, resp.text


async def test_mensaje_en_espanol_para_ticker_desconocido(api_auth_client):
    resp = await api_auth_client.post(INVEST, json=btc(ticker="FOOCOIN"))
    assert "No tenemos cotización automática para ese ticker" in resp.text


async def test_update_valida_el_estado_resultante(api_auth_client, db_session):
    await add_price(db_session, "BTC", "USD", "80000")
    manual = (await api_auth_client.post(INVEST, json=btc(price_source="manual", quantity=None))).json()
    url = f"{INVEST}/{manual['id']}"
    assert (await api_auth_client.put(url, json={"price_source": "coingecko"})).status_code == 422
    ok = await api_auth_client.put(url, json={"price_source": "coingecko", "quantity": "0.25"})
    assert ok.status_code == 200 and ok.json()["value_source"] == "quote"
    assert D(ok.json()["effective_value"]) == D("20000.00")
    # Borrar la cantidad de un automatico deja un estado invalido.
    assert (await api_auth_client.put(url, json={"quantity": None})).status_code == 422
    # Cambiar a un ticker sin cotizacion tambien.
    assert (await api_auth_client.put(url, json={"ticker": "FOOCOIN"})).status_code == 422
    # Una accion no puede pasar a automatica.
    stock = (await api_auth_client.post(INVEST, json={"asset_type": "stock", "name": "S", "currency": "ARS", "invested_amount": "10", "quantity": "1", "ticker": "AAPL"})).json()
    assert (await api_auth_client.put(f"{INVEST}/{stock['id']}", json={"price_source": "coingecko"})).status_code == 422


async def test_volver_a_manual(api_auth_client, db_session):
    await add_price(db_session, "BTC", "USD", "79509")
    auto = (await api_auth_client.post(INVEST, json=btc())).json()
    assert auto["value_source"] == "quote"
    back = await api_auth_client.put(
        f"{INVEST}/{auto['id']}", json={"price_source": "manual", "current_value": "30000"}
    )
    data = back.json()
    assert back.status_code == 200
    assert D(data["effective_value"]) == D("30000.00") and data["value_source"] == "manual"
    assert data["quote_provider"] is None and data["quote_stale"] is None


async def test_cambiar_ticker_descarta_el_precio_anterior(api_auth_client, db_session):
    await add_price(db_session, "BTC", "USD", "79509")
    auto = (await api_auth_client.post(INVEST, json=btc())).json()
    changed = (await api_auth_client.put(f"{INVEST}/{auto['id']}", json={"ticker": "ETH"})).json()
    assert changed["last_price"] is None and changed["value_source"] == "invested"


async def test_quote_stale_pasada_una_hora(api_auth_client, db_session):
    await add_price(db_session, "BTC", "USD", "79509", age_minutes=180)
    data = (await api_auth_client.post(INVEST, json=btc())).json()
    assert data["quote_stale"] is True
    await add_price(db_session, "ETH", "USD", "2500", age_minutes=30)
    fresh = (await api_auth_client.post(INVEST, json=btc(ticker="ETH"))).json()
    assert fresh["quote_stale"] is False


# ── Catalogo y kill switch ──────────────────────────────────────────────────


async def test_catalogo_de_criptos_sin_red(api_auth_client):
    data = (await api_auth_client.get("/api/v1/finance/market/crypto-assets")).json()
    assert {"ticker": "BTC", "name": "Bitcoin"} in data
    assert len(data) >= 20


async def test_kill_switch_apaga_la_cripto_automatica(api_auth_client, monkeypatch):
    monkeypatch.setattr(settings, "MARKET_CRYPTO_ENABLED", False)
    assert (await api_auth_client.get("/api/v1/finance/market/crypto-assets")).json() == []
    assert (await api_auth_client.post(INVEST, json=btc())).status_code == 422
    assert "crypto" not in scheduler.enabled_sources()
    assert (await api_auth_client.post(INVEST, json=btc(price_source="manual"))).status_code == 201

"""Cotizaciones del dolar y euro: providers, cadena de respaldo, sanidad,
historico diario, cotizacion efectiva del usuario y totales."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import func, select

from app.modules.mercado import service as market
from app.modules.mercado.models import FxQuote
from app.modules.mercado.providers import argentinadatos, bluelytics, dolarapi
from app.modules.mercado.providers.base import ProviderError
from market_helpers import (
    AD_PREFIX,
    BLUELYTICS,
    DOLARAPI_EUR,
    DOLARAPI_USD,
    FakeMarket,
    add_quote,
    at,
    fixture,
    set_state,
)

pytestmark = pytest.mark.asyncio

NOW = at("2026-10-26", 15)


def D(value) -> Decimal:
    return Decimal(str(value))


async def quotes(db, currency=None, kind=None):
    query = select(FxQuote).order_by(FxQuote.currency, FxQuote.kind, FxQuote.quote_date)
    if currency:
        query = query.where(FxQuote.currency == currency)
    if kind:
        query = query.where(FxQuote.kind == kind)
    return list((await db.execute(query)).scalars())


# ── Providers: parseo y normalizacion ───────────────────────────────────────


def test_dolarapi_normaliza_los_tipos():
    parsed = {(q.currency, q.kind): q for q in dolarapi.parse_dolares(fixture("dolarapi_dolares"))}
    assert set(parsed) == {
        ("USD", k) for k in ("oficial", "blue", "mep", "ccl", "mayorista", "cripto", "tarjeta")
    }
    mep = parsed[("USD", "mep")]
    assert mep.sell == D("1563.9") and mep.buy == D("1557.4")
    assert mep.provider == "dolarapi"
    assert mep.source_updated_at == at("2026-10-25", 20, 58)


def test_dolarapi_euro_y_items_malformados():
    eur = dolarapi.parse_eur(fixture("dolarapi_eur"))
    assert [(q.currency, q.kind) for q in eur] == [("EUR", "oficial")]
    assert dolarapi.parse_eur({"moneda": "EUR", "casa": "oficial"}) == []

    payload = fixture("dolarapi_dolares") + [
        {"moneda": "USD", "casa": "blue", "compra": 1, "fechaActualizacion": "2026-10-25T20:58:00Z"},
        "basura",
        {"casa": "desconocida", "venta": 5, "fechaActualizacion": "2026-10-25T20:58:00Z"},
    ]
    assert len(dolarapi.parse_dolares(payload)) == 7
    with pytest.raises(ProviderError):
        dolarapi.parse_dolares({"no": "lista"})


def test_bluelytics_y_argentinadatos():
    blue = {(q.currency, q.kind): q for q in bluelytics.parse_latest(fixture("bluelytics_latest"))}
    assert set(blue) == {("USD", "oficial"), ("USD", "blue"), ("EUR", "oficial"), ("EUR", "blue")}
    assert blue[("EUR", "blue")].sell == D("1698.00")
    assert blue[("USD", "blue")].source_updated_at.utcoffset() == timedelta(0)

    last = argentinadatos.parse_latest_fx(fixture("argentinadatos_bolsa"), "mep")
    assert len(last) == 1 and last[0].sell == D("1563.9") and last[0].provider == "argentinadatos"
    assert last[0].source_updated_at.date().isoformat() == "2026-10-26"


# ── refresh_fx: cadena de respaldo ──────────────────────────────────────────


async def test_dolarapi_trae_todo_y_bluelytics_solo_el_euro_blue(db_session):
    fake = FakeMarket()
    async with fake.client() as client:
        result = await market.refresh_fx(db_session, client, NOW)

    rows = await quotes(db_session)
    by = {(r.currency, r.kind): r for r in rows}
    assert len(rows) == 9  # 7 USD + EUR oficial (DolarAPI) + EUR blue (Bluelytics)
    mep = by[("USD", "mep")]
    assert D(mep.sell) == D("1563.9") and mep.provider == "dolarapi"
    assert mep.source_updated_at.replace(tzinfo=timezone.utc) == at("2026-10-25", 20, 58)
    assert by[("EUR", "blue")].provider == "bluelytics" and D(by[("EUR", "blue")].sell) == D("1698")
    # El oficial/blue de USD NO los pisa Bluelytics: el primario manda.
    assert by[("USD", "blue")].provider == "dolarapi"
    assert by[("USD", "oficial")].provider == "dolarapi"
    assert result.stored == 9
    assert fake.count(AD_PREFIX + "bolsa") == 0  # sin faltantes, no se consulta el 3er respaldo


async def test_dolarapi_caida_usa_bluelytics_y_argentinadatos(db_session):
    fake = FakeMarket()
    fake.fail(DOLARAPI_USD, DOLARAPI_EUR)
    async with fake.client() as client:
        result = await market.refresh_fx(db_session, client, NOW)

    by = {(r.currency, r.kind): r for r in await quotes(db_session)}
    assert by[("USD", "blue")].provider == "bluelytics" and D(by[("USD", "blue")].sell) == D("1562")
    assert by[("USD", "oficial")].provider == "bluelytics"
    assert by[("EUR", "oficial")].provider == "bluelytics"
    assert by[("USD", "mep")].provider == "argentinadatos"  # Bluelytics no tiene MEP
    assert ("USD", "ccl") not in by  # solo existe en DolarAPI
    assert len(result.errors) == 2


async def test_par_faltante_en_el_primario_se_completa_con_respaldo(db_session):
    fake = FakeMarket()
    fake.routes[DOLARAPI_USD] = [i for i in fixture("dolarapi_dolares") if i["casa"] != "bolsa"]
    async with fake.client() as client:
        await market.refresh_fx(db_session, client, NOW)
    mep = (await quotes(db_session, "USD", "mep"))[0]
    assert mep.provider == "argentinadatos"


async def test_todas_las_fuentes_caidas_levanta_error(db_session):
    fake = FakeMarket({})  # todo 404
    async with fake.client() as client:
        with pytest.raises(ProviderError):
            await market.refresh_fx(db_session, client, NOW)
    assert await quotes(db_session) == []


async def test_respaldo_viejo_no_pisa_dato_nuevo(db_session):
    newer = at("2026-10-25", 20, 58)
    await add_quote(db_session, "USD", "blue", 1565, buy=1545, as_of=newer)
    fake = FakeMarket()
    fake.fail(DOLARAPI_USD)
    # Bluelytics del mismo dia (hora de Argentina) pero mas viejo que lo guardado.
    fake.routes[BLUELYTICS] = {
        "oficial": {"value_sell": 1550, "value_buy": 1496},
        "blue": {"value_sell": 1500, "value_buy": 1480},
        "last_update": "2026-10-25T10:00:00-03:00",
    }
    async with fake.client() as client:
        await market.refresh_fx(db_session, client, NOW)
    blue = await quotes(db_session, "USD", "blue")
    assert len(blue) == 1 and D(blue[0].sell) == D("1565") and blue[0].provider == "dolarapi"


async def test_cotizacion_mas_nueva_actualiza_la_fila_del_dia(db_session):
    await add_quote(db_session, "USD", "blue", 1500, as_of=at("2026-10-26", 14))
    fake = FakeMarket()
    fake.routes[DOLARAPI_USD] = [
        {"moneda": "USD", "casa": "blue", "compra": 1540, "venta": 1520, "fechaActualizacion": "2026-10-26T18:00:00Z"}
    ]
    async with fake.client() as client:
        await market.refresh_fx(db_session, client, NOW)
    blue = await quotes(db_session, "USD", "blue")
    assert len(blue) == 1  # una fila por dia
    assert D(blue[0].sell) == D("1520") and D(blue[0].buy) == D("1540")


async def test_un_dia_nuevo_agrega_fila_y_conserva_el_cierre_anterior(db_session):
    await add_quote(db_session, "USD", "blue", 1500, as_of=at("2026-10-25", 20))
    fake = FakeMarket()
    fake.routes[DOLARAPI_USD] = [
        {"moneda": "USD", "casa": "blue", "compra": 1510, "venta": 1520, "fechaActualizacion": "2026-10-26T18:00:00Z"}
    ]
    async with fake.client() as client:
        await market.refresh_fx(db_session, client, NOW)
    blue = await quotes(db_session, "USD", "blue")
    assert [D(r.sell) for r in blue] == [D("1500"), D("1520")]


async def test_el_dia_se_cuenta_en_hora_argentina(db_session):
    # 01:30 UTC del 27 = 22:30 del 26 en Argentina.
    fake = FakeMarket()
    fake.routes[DOLARAPI_USD] = [
        {"moneda": "USD", "casa": "blue", "compra": 1510, "venta": 1520, "fechaActualizacion": "2026-10-27T01:30:00Z"}
    ]
    async with fake.client() as client:
        await market.refresh_fx(db_session, client, NOW)
    assert (await quotes(db_session, "USD", "blue"))[0].quote_date.isoformat() == "2026-10-26"


# ── Sanidad ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "item",
    [
        {"casa": "blue", "compra": 0, "venta": 0},
        {"casa": "blue", "compra": 1500, "venta": -5},
        {"casa": "blue", "compra": 1500, "venta": 20000000},
        {"casa": "blue", "compra": 3000, "venta": 1500},  # compra > 1,5 x venta
    ],
)
async def test_sanidad_descarta_valores_invalidos(db_session, item):
    fake = FakeMarket()
    fake.routes[DOLARAPI_USD] = [{"moneda": "USD", "fechaActualizacion": "2026-10-26T18:00:00Z", **item}]
    async with fake.client() as client:
        try:
            await market.refresh_fx(db_session, client, NOW)
        except ProviderError:
            pass
    blue = await quotes(db_session, "USD", "blue")
    # Lo unico que pudo guardarse es lo que trajo Bluelytics, nunca el item roto.
    assert all(r.provider != "dolarapi" for r in blue)


async def test_sanidad_descarta_salto_mayor_a_50_porciento(db_session):
    await add_quote(db_session, "USD", "mep", "1563.90", as_of=at("2026-10-25", 20))
    fake = FakeMarket()
    fake.routes[DOLARAPI_USD] = [
        {"moneda": "USD", "casa": "bolsa", "compra": 15000, "venta": 15639, "fechaActualizacion": "2026-10-26T18:00:00Z"}
    ]
    async with fake.client() as client:
        await market.refresh_fx(db_session, client, NOW)
    mep = await quotes(db_session, "USD", "mep")
    assert len(mep) == 1 and D(mep[0].sell) == D("1563.9")


async def test_item_malformado_no_tumba_a_los_validos(db_session):
    fake = FakeMarket()
    fake.routes[DOLARAPI_USD] = fixture("dolarapi_dolares") + [
        {"moneda": "USD", "casa": "blue", "compra": 1, "fechaActualizacion": "2026-10-26T18:00:00Z"}
    ]
    async with fake.client() as client:
        result = await market.refresh_fx(db_session, client, NOW)
    assert result.stored == 9


# ── Retencion ───────────────────────────────────────────────────────────────


async def test_retencion_de_730_dias_una_vez_por_dia(db_session):
    old = at("2026-10-26") - timedelta(days=800)
    await add_quote(db_session, "USD", "blue", 100, as_of=old)
    await add_quote(db_session, "USD", "blue", 900, as_of=at("2026-10-26") - timedelta(days=700))
    fake = FakeMarket()
    async with fake.client() as client:
        await market.refresh_fx(db_session, client, NOW)
    sells = [D(r.sell) for r in await quotes(db_session, "USD", "blue")]
    assert D("100") not in sells and D("900") in sells
    # Segunda corrida el mismo dia: no vuelve a borrar.
    await add_quote(db_session, "EUR", "oficial", 5, as_of=old)
    async with fake.client() as client:
        await market.refresh_fx(db_session, client, NOW)
    assert D("5") in [D(r.sell) for r in await quotes(db_session, "EUR", "oficial")]


# ── Endpoint /finance/market/fx ─────────────────────────────────────────────


async def test_endpoint_fx_lista_oficial_mep_blue_sin_red(api_auth_client, db_session):
    now = datetime.now(timezone.utc)
    await add_quote(db_session, "USD", "mep", "1563.9", buy="1557.4", as_of=now - timedelta(minutes=5))
    await add_quote(db_session, "USD", "blue", 1565, buy=1545, as_of=now - timedelta(minutes=5))
    await add_quote(db_session, "USD", "oficial", 1550, buy=1500, as_of=now - timedelta(minutes=5))
    await add_quote(db_session, "USD", "ccl", 1654, as_of=now)
    await add_quote(db_session, "EUR", "oficial", 1713, as_of=now)
    await set_state(db_session, "fx", last_success_at=now - timedelta(minutes=5))

    resp = await api_auth_client.get("/api/v1/finance/market/fx")
    assert resp.status_code == 200
    data = resp.json()
    assert [q["kind"] for q in data["usd"]] == ["oficial", "mep", "blue"]
    mep = data["usd"][1]
    assert mep["label"] == "MEP" and D(mep["sell"]) == D("1563.9") and D(mep["buy"]) == D("1557.4")
    assert mep["provider"] == "dolarapi" and mep["stale"] is False
    assert [q["kind"] for q in data["eur"]] == ["oficial"]
    assert data["degraded"] is False and data["last_success_at"] is not None


async def test_endpoint_fx_degraded_y_stale(api_auth_client, db_session):
    now = datetime.now(timezone.utc)
    await add_quote(db_session, "USD", "mep", 1500, as_of=now - timedelta(hours=7))
    await set_state(db_session, "fx", last_success_at=now - timedelta(hours=7), failures=2)
    data = (await api_auth_client.get("/api/v1/finance/market/fx")).json()
    assert data["degraded"] is True
    assert data["usd"][0]["stale"] is True  # el job lleva > 6 h sin exito


async def test_endpoint_fx_sin_datos_esta_degradado(api_auth_client):
    data = (await api_auth_client.get("/api/v1/finance/market/fx")).json()
    assert data["usd"] == [] and data["eur"] == [] and data["degraded"] is True


async def test_endpoints_de_mercado_exigen_login(client):
    for path in ("fx", "inflation", "crypto-assets"):
        assert (await client.get(f"/api/v1/finance/market/{path}")).status_code == 401


# ── Cotizacion efectiva del usuario ─────────────────────────────────────────

SETTINGS = "/api/v1/settings"
INVEST = "/api/v1/finance/investments"
SUMMARY = f"{INVEST}/summary"


async def invest(client, **overrides):
    body = {"asset_type": "other", "name": "Activo", "currency": "ARS", "invested_amount": "500000"}
    body.update(overrides)
    resp = await client.post(INVEST, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def seed_market(db, *, hours_ago=0):
    now = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    await add_quote(db, "USD", "mep", "1563.90", buy="1557.40", as_of=now)
    await add_quote(db, "USD", "blue", "1565", buy="1545", as_of=now)
    await add_quote(db, "USD", "oficial", "1550", buy="1500", as_of=now)
    await add_quote(db, "EUR", "oficial", "1713.9577", as_of=now)
    await set_state(db, "fx", last_success_at=now)


async def test_default_mep_aplicado_a_los_totales(api_auth_client, db_session):
    await seed_market(db_session)
    await invest(api_auth_client, name="Pesos")
    await invest(
        api_auth_client, asset_type="fx", name="Dolares", currency="USD", invested_amount="2000"
    )
    summary = (await api_auth_client.get(SUMMARY)).json()
    assert D(summary["total_ars"]) == D("3627800.00")  # 500000 + 2000 x 1563,90
    assert summary["missing_rates"] == []

    rates = (await api_auth_client.get("/api/v1/finance/net-worth")).json()["rates"]
    assert D(rates["usd_ars"]) == D("1563.9")
    assert rates["usd_source"] == "mep" and rates["usd_effective_source"] == "mep"
    assert rates["usd_provider"] == "dolarapi" and rates["usd_stale"] is False
    assert D(rates["usd_buy"]) == D("1557.4")
    assert rates["updated_at"] == rates["usd_as_of"]


async def test_cambiar_de_fuente_cambia_totales_y_patrimonio(api_auth_client, db_session):
    await seed_market(db_session)
    await invest(
        api_auth_client, asset_type="fx", name="Dolares", currency="USD", invested_amount="1000"
    )
    for source, rate in (("blue", "1565"), ("oficial", "1550"), ("mep", "1563.9")):
        put = await api_auth_client.put(SETTINGS, json={"fx_usd_source": source})
        assert put.status_code == 200 and put.json()["fx_usd_source"] == source
        summary = (await api_auth_client.get(SUMMARY)).json()
        assert D(summary["total_ars"]) == D(rate) * 1000
        finance = (await api_auth_client.get("/api/v1/finance/summary")).json()
        assert D(finance["investments_value_ars"]) == D(rate) * 1000


async def test_manual_usa_la_cotizacion_propia_y_volver_la_recupera(api_auth_client, db_session):
    await seed_market(db_session)
    await invest(
        api_auth_client, asset_type="fx", name="Dolares", currency="USD", invested_amount="100"
    )
    await api_auth_client.put(SETTINGS, json={"fx_usd_ars": "1450.50", "fx_usd_source": "manual"})
    rates = (await api_auth_client.get("/api/v1/finance/net-worth")).json()["rates"]
    assert D(rates["usd_ars"]) == D("1450.50") and rates["usd_effective_source"] == "manual"
    assert rates["usd_provider"] is None

    # Cambiar a una automatica no borra la manual...
    put = (await api_auth_client.put(SETTINGS, json={"fx_usd_source": "mep"})).json()
    assert D(put["fx_usd_ars"]) == D("1450.5")
    # ...y volver a manual la recupera.
    back = (await api_auth_client.put(SETTINGS, json={"fx_usd_source": "manual"})).json()
    assert D(back["fx_usd_ars"]) == D("1450.5") and back["fx_usd_source"] == "manual"


async def test_api_caida_sigue_con_la_ultima_conocida(api_auth_client, db_session):
    # Los ultimos datos tienen 3 h y el job falla desde entonces.
    await seed_market(db_session, hours_ago=3)
    await set_state(
        db_session,
        "fx",
        last_success_at=datetime.now(timezone.utc) - timedelta(hours=3),
        failures=5,
    )
    await invest(
        api_auth_client, asset_type="fx", name="Dolares", currency="USD", invested_amount="10"
    )
    await api_auth_client.put(SETTINGS, json={"fx_usd_source": "blue"})
    summary = (await api_auth_client.get(SUMMARY)).json()
    assert D(summary["total_ars"]) == D("15650")
    rates = (await api_auth_client.get("/api/v1/finance/net-worth")).json()["rates"]
    assert rates["usd_effective_source"] == "blue" and rates["usd_stale"] is False


async def test_sin_datos_usa_la_manual_como_fallback(api_auth_client):
    await api_auth_client.put(SETTINGS, json={"fx_usd_ars": "1400"})  # source sigue en mep
    await invest(
        api_auth_client, asset_type="fx", name="Dolares", currency="USD", invested_amount="10"
    )
    rates = (await api_auth_client.get("/api/v1/finance/net-worth")).json()["rates"]
    assert D(rates["usd_ars"]) == D("1400")
    assert rates["usd_source"] == "mep" and rates["usd_effective_source"] == "manual_fallback"
    assert (await api_auth_client.get(SUMMARY)).json()["total_ars"] == "14000.00"


async def test_sin_datos_ni_manual_va_a_missing_rates(api_auth_client):
    await invest(
        api_auth_client, asset_type="fx", name="Dolares", currency="USD", invested_amount="10"
    )
    summary = (await api_auth_client.get(SUMMARY)).json()
    assert summary["total_ars"] is None and summary["missing_rates"] == ["USD"]
    nw = (await api_auth_client.get("/api/v1/finance/net-worth")).json()
    assert nw["rates"]["usd_ars"] is None and "USD" in nw["missing_rates"]
    assert nw["rates"]["usd_effective_source"] is None


@pytest.mark.parametrize(
    "as_of_hours, success_hours, expected",
    [(100, 0.1, True), (95, 0.1, False), (1, 7, True), (1, 5, False)],
)
async def test_stale(api_auth_client, db_session, as_of_hours, success_hours, expected):
    now = datetime.now(timezone.utc)
    await add_quote(db_session, "USD", "mep", 1500, as_of=now - timedelta(hours=as_of_hours))
    await set_state(db_session, "fx", last_success_at=now - timedelta(hours=success_hours))
    rates = (await api_auth_client.get("/api/v1/finance/net-worth")).json()["rates"]
    assert rates["usd_stale"] is expected


async def test_euro_oficial_automatico(api_auth_client, db_session):
    await seed_market(db_session)
    await invest(
        api_auth_client, asset_type="fx", name="Euros", currency="EUR", invested_amount="100"
    )
    summary = (await api_auth_client.get(SUMMARY)).json()
    assert D(summary["total_ars"]) == D("171395.77")
    rates = (await api_auth_client.get("/api/v1/finance/net-worth")).json()["rates"]
    assert rates["eur_source"] == "oficial" and rates["eur_effective_source"] == "oficial"


# ── Preferencias ────────────────────────────────────────────────────────────


async def test_settings_fuentes_por_defecto(api_auth_client):
    data = (await api_auth_client.get(SETTINGS)).json()
    assert data["fx_usd_source"] == "mep" and data["fx_eur_source"] == "oficial"


@pytest.mark.parametrize(
    "body",
    [
        {"fx_usd_source": "ccl"},
        {"fx_usd_source": "MEP"},
        {"fx_usd_source": ""},
        {"fx_eur_source": "mep"},
        {"fx_eur_source": "tarjeta"},
        {"fx_usd_source": 5},
    ],
)
async def test_settings_fuente_invalida_es_422(api_auth_client, body):
    assert (await api_auth_client.put(SETTINGS, json=body)).status_code == 422


async def test_settings_fuente_nula_se_ignora(api_auth_client):
    await api_auth_client.put(SETTINGS, json={"fx_usd_source": "blue", "fx_eur_source": "blue"})
    data = (await api_auth_client.put(SETTINGS, json={"fx_usd_source": None})).json()
    assert data["fx_usd_source"] == "blue" and data["fx_eur_source"] == "blue"

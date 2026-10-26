"""IPC: serie, inflacion acumulada con meses parciales/estimados y rendimiento
real por activo y de cartera."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.clock import local_today
from app.modules.inversiones.service import build_summary, real_return_for, to_out
from app.modules.inversiones.valuation import Rates, valuate
from app.modules.mercado import inflation as infl
from app.modules.mercado import service as market
from app.modules.mercado.models import InflationMonth
from app.modules.mercado.providers import argentinadatos, datos_gob
from app.modules.mercado.providers.base import ProviderError
from market_helpers import (
    AD_INFLATION,
    DATOS_GOB,
    FakeMarket,
    add_inflation,
    at,
    fixture,
    months_back,
)

pytestmark = pytest.mark.asyncio


def D(value) -> Decimal:
    return Decimal(str(value))


def P(year, month) -> date:
    return date(year, month, 1)


SERIES = {P(2026, 7): D("2.1"), P(2026, 8): D("1.7"), P(2026, 9): D("1.9")}


# ── Factor acumulado (puro) ─────────────────────────────────────────────────


def test_mes_completo_publicado():
    acc = infl.accumulated_factor(SERIES, date(2026, 9, 1), date(2026, 10, 1))
    assert round(acc.inflation_pct, 2) == D("1.90")
    assert acc.estimated is False and acc.estimated_months == ()


def test_mes_parcial_prorrateo_geometrico():
    acc = infl.accumulated_factor(SERIES, date(2026, 9, 16), date(2026, 10, 1))
    assert acc.inflation_pct.quantize(D("0.01")) == D("0.95")  # 1,019^(15/30) - 1
    assert abs(acc.factor - D("1.019") ** (D(15) / D(30))) < D("1e-20")


def test_varios_meses_se_componen():
    acc = infl.accumulated_factor(SERIES, date(2026, 8, 1), date(2026, 10, 1))
    assert acc.factor == D("1.017") * D("1.019")


def test_mes_en_curso_sin_publicar_se_estima_con_el_ultimo_dato():
    acc = infl.accumulated_factor(SERIES, date(2026, 9, 1), date(2026, 10, 25))
    assert acc.estimated is True and acc.estimated_months == ("2026-10",)
    expected = D("1.019") * D("1.019") ** (D(24) / D(31))
    assert abs(acc.factor - expected) < D("1e-20")


def test_dos_meses_sin_publicar():
    acc = infl.accumulated_factor(SERIES, date(2026, 9, 15), date(2026, 11, 10))
    assert acc.estimated_months == ("2026-10", "2026-11")


def test_inicio_anterior_a_la_serie_no_da_resultado():
    assert infl.accumulated_factor(SERIES, date(2026, 6, 1), date(2026, 9, 1)) is None
    assert infl.accumulated_factor({}, date(2026, 6, 1), date(2026, 9, 1)) is None


# ── Rendimiento real (puro) ─────────────────────────────────────────────────


def test_plazo_fijo_ejemplo_del_diseno():
    # 1.000.000 al 30 % TNA, 30 dias: interes 24.657,53 -> nominal 2,47 %.
    rr, reason = infl.compute_real_return(
        invested=D("1000000"),
        value=D("1024657.53"),
        start=date(2026, 9, 1),
        end=date(2026, 10, 1),
        series=SERIES,
    )
    assert reason is None
    assert (rr.nominal_pct, rr.inflation_pct, rr.real_pct) == (D("2.47"), D("1.90"), D("0.56"))
    assert rr.estimated is False


def test_perdida_contra_la_inflacion():
    series = {P(2026, 9): D("3.0")}
    rr, _ = infl.compute_real_return(
        invested=D("100000"),
        value=D("101000"),
        start=date(2026, 9, 1),
        end=date(2026, 10, 1),
        series=series,
    )
    assert (rr.nominal_pct, rr.inflation_pct, rr.real_pct) == (D("1.00"), D("3.00"), D("-1.94"))


def test_motivos_sin_resultado():
    kw = dict(invested=D("100"), value=D("100"), series=SERIES)
    assert infl.compute_real_return(start=date(2026, 9, 5), end=date(2026, 9, 5), **kw)[1] == "too_short"
    assert infl.compute_real_return(start=date(2026, 10, 5), end=date(2026, 9, 5), **kw)[1] == "too_short"
    assert infl.compute_real_return(start=date(2025, 1, 5), end=date(2026, 9, 5), **kw)[1] == "no_inflation_data"
    zero = dict(invested=D("0"), value=D("0"), series=SERIES)
    assert infl.compute_real_return(start=date(2026, 9, 1), end=date(2026, 9, 9), **zero)[1] == "no_invested_amount"


def test_proyeccion_al_vencimiento_es_estimada():
    series = {P(2026, 9): D("1.9")}
    proj = infl.project_fixed_term(
        invested=D("1000000"),
        interest_total=D("24657.53"),
        start=date(2026, 10, 10),
        maturity=date(2026, 11, 9),
        series=series,
    )
    assert proj.estimated is True
    assert proj.nominal_pct == D("2.47")
    expected = D("1.019") ** (D(22) / D(31)) * D("1.019") ** (D(8) / D(30))
    assert proj.inflation_pct == ((expected - 1) * 100).quantize(D("0.01"))


def test_agregado_de_cartera_pondera_por_monto():
    a, _ = infl.compute_real_return(
        invested=D("1000000"), value=D("1024657.53"), start=date(2026, 9, 1), end=date(2026, 10, 1), series=SERIES
    )
    b, _ = infl.compute_real_return(
        invested=D("500000"), value=D("500000"), start=date(2026, 9, 1), end=date(2026, 10, 1), series=SERIES
    )
    port = infl.portfolio_real_return([a, b, None])
    assert port.included_count == 2 and port.excluded_count == 1
    assert port.nominal_pct == D("1.64")  # 1.524.657,53 / 1.500.000 - 1
    assert port.inflation_pct == D("1.90")
    assert port.real_pct == ((D("1524657.53") / (D("1500000") * D("1.019")) - 1) * 100).quantize(D("0.01"))
    assert infl.portfolio_real_return([None, None]) is None
    assert infl.portfolio_real_return([]) is None


# ── Por activo (service) ────────────────────────────────────────────────────


def make_inv(**kw):
    base = dict(
        id="1",
        user_id="u",
        asset_type="fixed_term",
        name="PF",
        ticker=None,
        currency="ARS",
        quantity=None,
        invested_amount=D("1000000"),
        current_value=None,
        interest_rate_tna=D("30"),
        start_date=date(2026, 9, 1),
        maturity_date=date(2026, 10, 1),
        status="active",
        price_source="manual",
        last_price=None,
        last_price_at=None,
        updated_at=datetime(2026, 9, 20, tzinfo=timezone.utc),
    )
    base.update(kw)
    return SimpleNamespace(**base)


def rr_for(inv, today):
    return real_return_for(inv, valuate(inv, today), today, SERIES)


def test_plazo_fijo_vencido_frena_en_el_vencimiento():
    rr, reason = rr_for(make_inv(), date(2026, 10, 20))
    assert reason is None and rr.period_end == date(2026, 10, 1)
    assert (rr.nominal_pct, rr.inflation_pct, rr.real_pct) == (D("2.47"), D("1.90"), D("0.56"))
    assert rr.projected_at_maturity is None


def test_plazo_fijo_activo_tiene_proyeccion():
    rr, _ = rr_for(make_inv(), date(2026, 9, 16))
    assert rr.period_end == date(2026, 9, 16)
    assert rr.projected_at_maturity.nominal_pct == D("2.47")
    assert rr.projected_at_maturity.real_pct == D("0.56")


@pytest.mark.parametrize(
    "overrides, reason",
    [
        ({"currency": "USD"}, "currency"),
        ({"currency": "USDT"}, "currency"),
        ({"asset_type": "stock", "start_date": None, "maturity_date": None, "interest_rate_tna": None}, "no_start_date"),
        ({"start_date": date(2026, 9, 16)}, "too_short"),  # S == hoy
        ({"start_date": date(2026, 11, 1), "maturity_date": date(2026, 12, 1)}, "too_short"),  # futura
        ({"start_date": date(2024, 1, 1)}, "no_inflation_data"),
    ],
)
def test_motivos_por_activo(overrides, reason):
    rr, got = rr_for(make_inv(**overrides), date(2026, 9, 16))
    assert rr is None and got == reason


def test_activo_cerrado_termina_en_vencimiento_o_ultima_actualizacion():
    closed_past = make_inv(status="closed")
    rr, _ = rr_for(closed_past, date(2026, 10, 20))
    assert rr.period_end == date(2026, 10, 1)
    closed_early = make_inv(status="closed", maturity_date=date(2026, 12, 1))
    rr, _ = rr_for(closed_early, date(2026, 10, 20))
    assert rr.period_end == date(2026, 9, 20)
    assert rr.projected_at_maturity is None


def test_to_out_sin_serie_dice_que_no_hay_datos():
    from app.modules.inversiones.models import Investment

    inv = Investment(
        id="1", user_id="u", asset_type="fixed_term", name="PF", currency="ARS",
        invested_amount=D("1000000"), interest_rate_tna=D("30"), status="active",
        start_date=date(2026, 9, 1), maturity_date=date(2026, 10, 1),
        notify_maturity=True, price_source="manual",
    )
    out = to_out(inv, date(2026, 10, 20), None)
    assert out.real_return is None and out.real_return_unavailable_reason == "no_inflation_data"


def test_resumen_cuenta_incluidos_y_excluidos():
    today = date(2026, 10, 20)
    rows = []
    for inv in (
        make_inv(id="a"),
        make_inv(id="b", asset_type="stock", start_date=None, maturity_date=None, interest_rate_tna=None),
        make_inv(id="c", currency="USD"),
    ):
        rows.append((inv, valuate(inv, today)))
    summary = build_summary(rows, Rates(usd_ars=D("1500")), today, SERIES)
    real = summary.real_return_ars
    assert real.included_count == 1 and real.excluded_count == 1  # el USD ni se cuenta
    only_usd = build_summary([rows[2]], Rates(usd_ars=D("1500")), today, SERIES)
    assert only_usd.real_return_ars is None


# ── Job de la serie ─────────────────────────────────────────────────────────


def test_argentinadatos_normaliza_el_periodo_al_dia_1():
    parsed = argentinadatos.parse_inflation(fixture("argentinadatos_inflacion"))
    last = parsed[-1]
    assert last.period == date(2026, 9, 1) and last.pct == D("1.9")
    assert argentinadatos.parse_inflation([{"fecha": "1999-01-31", "valor": 5}]) == []  # antes de 2017
    with pytest.raises(ProviderError):
        argentinadatos.parse_inflation({"x": 1})


def test_datos_gob_pasa_la_fraccion_a_porcentaje():
    parsed = datos_gob.parse_series(fixture("datos_gob_ipc"))
    assert parsed[0].period == date(2026, 2, 1) and parsed[0].pct == D("2.8963")
    assert all(p.provider == "datos_gob" for p in parsed)


async def test_refresh_inflation_guarda_la_serie(db_session):
    fake = FakeMarket()
    async with fake.client() as client:
        changed = await market.refresh_inflation(db_session, client, at("2026-10-26"))
    rows = {r.period: r for r in (await db_session.execute(select(InflationMonth))).scalars()}
    assert changed == len(rows) == 21
    assert D(rows[date(2026, 9, 1)].pct) == D("1.9") and rows[date(2026, 9, 1)].provider == "argentinadatos"
    assert fake.count(DATOS_GOB) == 0


async def test_refresh_inflation_respaldo_datos_gob(db_session):
    fake = FakeMarket()
    fake.fail(AD_INFLATION)
    async with fake.client() as client:
        await market.refresh_inflation(db_session, client, at("2026-10-26"))
    rows = (await db_session.execute(select(InflationMonth))).scalars().all()
    assert {r.provider for r in rows} == {"datos_gob"} and len(rows) == 7


async def test_respaldo_no_pisa_y_el_primario_corrige_revisiones(db_session):
    await add_inflation(db_session, {"2026-08": 1.5}, provider="argentinadatos")
    fake = FakeMarket()
    fake.fail(AD_INFLATION)
    async with fake.client() as client:
        await market.refresh_inflation(db_session, client, at("2026-10-26"))
    august = await db_session.get(InflationMonth, date(2026, 8, 1))
    assert D(august.pct) == D("1.5")  # el respaldo no pisa

    fake2 = FakeMarket()
    async with fake2.client() as client:
        await market.refresh_inflation(db_session, client, at("2026-10-26"))
    await db_session.refresh(august)
    assert D(august.pct) == D("1.7")  # revision: gana el primario


async def test_sanidad_de_la_serie(db_session):
    fake = FakeMarket()
    fake.routes[AD_INFLATION] = [
        {"fecha": "2026-06-30", "valor": 2.1},
        {"fecha": "2026-07-31", "valor": 150},  # fuera de rango
        {"fecha": "2026-08-31", "valor": -30},  # fuera de rango
        {"fecha": "2026-11-30", "valor": 2.0},  # mes futuro
        {"fecha": "2026-09-30", "valor": "x"},  # no numerico
    ]
    async with fake.client() as client:
        await market.refresh_inflation(db_session, client, at("2026-10-26"))
    rows = (await db_session.execute(select(InflationMonth))).scalars().all()
    assert [r.period for r in rows] == [date(2026, 6, 1)]


async def test_sin_ninguna_fuente_levanta_error(db_session):
    fake = FakeMarket({})
    async with fake.client() as client:
        with pytest.raises(ProviderError):
            await market.refresh_inflation(db_session, client, at("2026-10-26"))


# ── API ─────────────────────────────────────────────────────────────────────

INVEST = "/api/v1/finance/investments"


async def test_endpoint_de_inflacion(api_auth_client, db_session):
    empty = (await api_auth_client.get("/api/v1/finance/market/inflation")).json()
    assert empty == {"series": [], "last_published_period": None, "estimate_pct": None}

    await add_inflation(db_session, {"2026-06": 2.1, "2026-07": 2.1, "2026-08": 1.7, "2026-09": 1.9})
    data = (await api_auth_client.get("/api/v1/finance/market/inflation?months=3")).json()
    assert [p["period"] for p in data["series"]] == ["2026-07", "2026-08", "2026-09"]
    assert data["last_published_period"] == "2026-09" and D(data["estimate_pct"]) == D("1.9")
    for bad in (0, 121):
        assert (await api_auth_client.get(f"/api/v1/finance/market/inflation?months={bad}")).status_code == 422


async def test_api_plazo_fijo_con_rendimiento_real_estimado(api_auth_client, db_session):
    today = local_today(-180)
    prev = months_back(14)
    await add_inflation(db_session, {m: 2.0 for m in prev})
    start = today - timedelta(days=12)
    resp = await api_auth_client.post(
        INVEST,
        json={
            "asset_type": "fixed_term",
            "name": "PF",
            "currency": "ARS",
            "invested_amount": "1000000",
            "interest_rate_tna": "30",
            "start_date": start.isoformat(),
            "maturity_date": (today + timedelta(days=18)).isoformat(),
            "timezone_offset_minutes": -180,
        },
    )
    assert resp.status_code == 201, resp.text
    rr = resp.json()["real_return"]
    assert rr["period_start"] == start.isoformat() and rr["period_end"] == today.isoformat()
    assert rr["inflation_pct"] != "0.00" and rr["projected_at_maturity"]["estimated"] is True
    # El mes en curso nunca esta publicado: sale marcado como estimado.
    assert rr["estimated"] is True and f"{today.year:04d}-{today.month:02d}" in rr["estimated_months"]
    assert resp.json()["real_return_unavailable_reason"] is None

    summary = (await api_auth_client.get(f"{INVEST}/summary")).json()
    assert summary["real_return_ars"]["included_count"] == 1
    listed = (await api_auth_client.get(INVEST)).json()[0]
    assert listed["real_return"]["real_pct"] == rr["real_pct"]


async def test_api_motivos_de_no_rendimiento(api_auth_client, db_session):
    await add_inflation(db_session, {m: 2.0 for m in months_back(14)})
    usd = await api_auth_client.post(
        INVEST,
        json={
            "asset_type": "fx",
            "name": "USD",
            "currency": "USD",
            "invested_amount": "100",
            "start_date": "2026-01-10",
        },
    )
    assert usd.json()["real_return"] is None and usd.json()["real_return_unavailable_reason"] == "currency"
    ars = await api_auth_client.post(
        INVEST, json={"asset_type": "stock", "name": "S", "currency": "ARS", "invested_amount": "100"}
    )
    assert ars.json()["real_return_unavailable_reason"] == "no_start_date"
    assert (await api_auth_client.get(f"{INVEST}/summary")).json()["real_return_ars"] is None

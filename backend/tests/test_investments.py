"""API de inversiones: CRUD, validaciones (422, nunca 500), orden y resumen."""

from datetime import timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.clock import local_today
from app.main import app
from app.modules.inversiones.models import Investment

pytestmark = pytest.mark.asyncio

URL = "/api/v1/finance/investments"


def D(value) -> Decimal:
    return Decimal(str(value))


def stock(**overrides):
    body = {
        "asset_type": "stock",
        "name": "Apple CEDEAR",
        "ticker": "aapl",
        "currency": "ARS",
        "quantity": "10",
        "invested_amount": "150000",
        "current_value": "172500",
    }
    body.update(overrides)
    return body


def fixed_term(**overrides):
    today = local_today(-180)
    body = {
        "asset_type": "fixed_term",
        "name": "Plazo fijo Galicia",
        "currency": "ARS",
        "invested_amount": "1000000",
        "interest_rate_tna": "30",
        "start_date": (today - timedelta(days=12)).isoformat(),
        "maturity_date": (today + timedelta(days=18)).isoformat(),
        "timezone_offset_minutes": -180,
    }
    body.update(overrides)
    return body


async def create(client, body, expected=201):
    resp = await client.post(URL, json=body)
    assert resp.status_code == expected, resp.text
    return resp.json()


# ── Alta ────────────────────────────────────────────────────────────────────


async def test_crear_posicion_de_acciones(api_auth_client):
    data = await create(api_auth_client, stock())
    assert data["ticker"] == "AAPL"
    assert data["status"] == "active"
    assert data["price_source"] == "manual"
    assert D(data["effective_value"]) == D("172500.00")
    assert D(data["gain"]) == D("22500.00")
    assert D(data["gain_pct"]) == D("15.00")
    assert data["value_source"] == "manual"
    assert data["fixed_term"] is None
    assert data["value_updated_at"] is not None
    assert "eve_notice_for" not in data and "day_notice_for" not in data


async def test_crear_requiere_autenticacion(client):
    assert (await client.post(URL, json=stock())).status_code == 401
    assert (await client.get(URL)).status_code == 401
    assert (await client.get(f"{URL}/summary")).status_code == 401
    assert (await client.get("/api/v1/finance/net-worth")).status_code == 401


async def test_disponible_sin_comprar_ninguna_plantilla(api_auth_client):
    # Finanzas es plantilla base: no hay chequeo de entitlement.
    await create(api_auth_client, stock())


async def test_cripto_conserva_los_8_decimales(api_auth_client):
    data = await create(
        api_auth_client,
        stock(asset_type="crypto", name="BTC", ticker="btc", currency="USD", quantity="0.00012345"),
    )
    assert D(data["quantity"]) == D("0.00012345")
    fetched = (await api_auth_client.get(f"{URL}/{data['id']}")).json()
    assert D(fetched["quantity"]) == D("0.00012345")


async def test_ticker_vacio_se_guarda_como_null(api_auth_client):
    data = await create(api_auth_client, stock(ticker="   "))
    assert data["ticker"] is None


async def test_nombre_se_recorta(api_auth_client):
    data = await create(api_auth_client, stock(name="  Mi accion  "))
    assert data["name"] == "Mi accion"


async def test_monto_con_mas_de_dos_decimales_se_redondea(api_auth_client):
    data = await create(api_auth_client, stock(invested_amount="100.555", current_value=None))
    assert D(data["invested_amount"]) == D("100.56")


# ── Plazo fijo ──────────────────────────────────────────────────────────────


async def test_plazo_fijo_calcula_interes_y_devengado(api_auth_client):
    data = await create(api_auth_client, fixed_term())
    ft = data["fixed_term"]
    assert ft["term_days"] == 30
    assert D(ft["interest_total"]) == D("24657.53")
    assert D(ft["amount_at_maturity"]) == D("1024657.53")
    assert D(ft["accrued_interest"]) == D("9863.01")
    assert D(ft["tea_pct"]) == D("34.50")
    assert D(data["effective_value"]) == D("1009863.01")
    assert data["value_source"] == "fixed_term_accrued"
    assert data["days_to_maturity"] == 18
    assert data["is_matured"] is False


async def test_devengado_usa_el_offset_del_get(api_auth_client):
    await create(api_auth_client, fixed_term())
    # El mismo plazo fijo visto desde un huso que ya cambio de dia (+14h):
    # el "hoy" del usuario se adelanta y el devengado tambien.
    far_east = (await api_auth_client.get(URL, params={"tz_offset_minutes": 840})).json()[0]
    west = (await api_auth_client.get(URL, params={"tz_offset_minutes": -180})).json()[0]
    assert far_east["days_to_maturity"] <= west["days_to_maturity"]
    assert D(far_east["fixed_term"]["accrued_interest"]) >= D(west["fixed_term"]["accrued_interest"])


async def test_plazo_fijo_vencido_frena_el_devengado(api_auth_client):
    today = local_today(-180)
    data = await create(
        api_auth_client,
        fixed_term(
            start_date=(today - timedelta(days=40)).isoformat(),
            maturity_date=(today - timedelta(days=10)).isoformat(),
        ),
    )
    assert data["is_matured"] is True
    assert data["days_to_maturity"] == -10
    assert data["fixed_term"]["accrued_interest"] == data["fixed_term"]["interest_total"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"interest_rate_tna": None},
        {"currency": "EUR"},
        {"currency": "USDT"},
        {"start_date": None},
        {"maturity_date": None},
        {"maturity_date": "2000-01-01", "start_date": "2000-01-01"},
    ],
    ids=["sin-tna", "eur", "usdt", "sin-inicio", "sin-vencimiento", "vence-el-mismo-dia"],
)
async def test_plazo_fijo_invalido_es_422(api_auth_client, overrides):
    await create(api_auth_client, fixed_term(**overrides), expected=422)


async def test_plazo_fijo_en_dolares_es_valido(api_auth_client):
    await create(api_auth_client, fixed_term(currency="USD", interest_rate_tna="2.5"))


# ── Limites: 422, nunca 500 ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "overrides",
    [
        {"invested_amount": "10000000000"},
        {"invested_amount": "9999999999.99999"},
        {"current_value": "10000000000"},
        {"invested_amount": "-1"},
        {"current_value": "-1"},
        {"quantity": "-1"},
        {"quantity": "1000000000000"},
        {"quantity": "0.123456789"},
        {"interest_rate_tna": "1000"},
        {"interest_rate_tna": "-1"},
        {"interest_rate_tna": "10.12345"},
        {"ticker": "con espacio"},
        {"ticker": "A" * 21},
        {"ticker": "ab$"},
        {"currency": "BTC"},
        {"asset_type": "nft"},
        {"price_source": "coingecko"},
        {"name": ""},
        {"name": "   "},
        {"name": "x" * 121},
        {"institution": "x" * 121},
        {"notes": "x" * 2001},
        {"timezone_offset_minutes": 841},
        {"timezone_offset_minutes": -841},
        {"start_date": "1969-12-31"},
        {"maturity_date": "2101-01-01", "start_date": "2026-01-01"},
        {"start_date": "2026-10-10", "maturity_date": "2026-10-01"},
        {"invested_amount": "NaN"},
        {"invested_amount": "Infinity"},
        {"invested_amount": "abc"},
    ],
)
async def test_valores_fuera_de_limite_son_422(api_auth_client, overrides):
    resp = await api_auth_client.post(URL, json=stock(**overrides))
    assert resp.status_code == 422, resp.text


async def test_en_el_limite_exacto_se_acepta(api_auth_client):
    data = await create(
        api_auth_client,
        stock(invested_amount="9999999999.99", current_value="9999999999.99", interest_rate_tna="999.9999"),
    )
    assert D(data["invested_amount"]) == D("9999999999.99")


async def test_borde_de_fechas(api_auth_client):
    await create(
        api_auth_client,
        stock(asset_type="other", start_date="1970-01-01", maturity_date="2100-12-31"),
    )


async def test_update_con_limites_invalidos_es_422(api_auth_client):
    inv = await create(api_auth_client, stock())
    for body in (
        {"invested_amount": "10000000000"},
        {"current_value": "-5"},
        {"ticker": "$$"},
        {"price_source": "binance"},
        {"status": "archived"},
        {"timezone_offset_minutes": 9999},
    ):
        resp = await api_auth_client.put(f"{URL}/{inv['id']}", json=body)
        assert resp.status_code == 422, (body, resp.text)


# ── Lectura, lista y orden ──────────────────────────────────────────────────


async def test_lista_ordenada_por_tipo_vencimiento_y_nombre(api_auth_client):
    today = local_today(-180)
    plus = lambda n: (today + timedelta(days=n)).isoformat()  # noqa: E731
    await create(api_auth_client, fixed_term(name="PF lejano", maturity_date=plus(90)))
    await create(api_auth_client, fixed_term(name="PF cercano", maturity_date=plus(10)))
    await create(api_auth_client, stock(name="Zeta", ticker=None))
    await create(api_auth_client, stock(name="Alfa", ticker=None))
    await create(api_auth_client, stock(asset_type="bond", name="Bono", ticker=None))

    names = [i["name"] for i in (await api_auth_client.get(URL)).json()]
    # bond < fixed_term < stock; dentro del plazo fijo, vencimiento ascendente;
    # dentro de stock (sin vencimiento), por nombre.
    assert names == ["Bono", "PF cercano", "PF lejano", "Alfa", "Zeta"]


async def test_los_sin_vencimiento_van_al_final_de_su_tipo(api_auth_client):
    today = local_today(-180)
    await create(api_auth_client, stock(asset_type="bond", name="Sin venc", ticker=None))
    await create(
        api_auth_client,
        stock(
            asset_type="bond",
            name="Con venc",
            ticker=None,
            maturity_date=(today + timedelta(days=400)).isoformat(),
        ),
    )
    names = [i["name"] for i in (await api_auth_client.get(URL)).json()]
    assert names == ["Con venc", "Sin venc"]


async def test_filtro_por_estado_y_tipo(api_auth_client):
    a = await create(api_auth_client, stock(name="Abierta", ticker=None))
    b = await create(api_auth_client, stock(name="Cerrada", ticker=None))
    await create(api_auth_client, stock(asset_type="crypto", name="Cripto", ticker=None))
    await api_auth_client.put(f"{URL}/{b['id']}", json={"status": "closed"})

    def names(resp):
        return sorted(i["name"] for i in resp.json())

    assert names(await api_auth_client.get(URL)) == ["Abierta", "Cripto"]
    assert names(await api_auth_client.get(URL, params={"status": "closed"})) == ["Cerrada"]
    assert names(await api_auth_client.get(URL, params={"status": "all"})) == [
        "Abierta",
        "Cerrada",
        "Cripto",
    ]
    assert names(await api_auth_client.get(URL, params={"asset_type": "crypto"})) == ["Cripto"]
    assert (await api_auth_client.get(URL, params={"status": "borrado"})).status_code == 422
    assert (await api_auth_client.get(URL, params={"asset_type": "nft"})).status_code == 422
    assert (await api_auth_client.get(URL, params={"tz_offset_minutes": 900})).status_code == 422
    assert a["id"]


async def test_get_por_id_y_404(api_auth_client):
    inv = await create(api_auth_client, stock())
    assert (await api_auth_client.get(f"{URL}/{inv['id']}")).status_code == 200
    assert (await api_auth_client.get(f"{URL}/no-existe")).status_code == 404


async def test_dias_al_vencimiento_respeta_el_tz_del_get(api_auth_client):
    today = local_today(0)
    await create(
        api_auth_client,
        stock(asset_type="bond", ticker=None, maturity_date=(today + timedelta(days=5)).isoformat()),
    )
    data = (await api_auth_client.get(URL, params={"tz_offset_minutes": 0})).json()[0]
    assert data["days_to_maturity"] == 5


# ── Update ──────────────────────────────────────────────────────────────────


async def test_update_parcial_no_toca_el_resto_y_marca_value_updated_at(api_auth_client):
    inv = await create(api_auth_client, stock(current_value=None))
    assert inv["value_updated_at"] is None

    resp = await api_auth_client.put(f"{URL}/{inv['id']}", json={"current_value": "200000"})
    assert resp.status_code == 200
    data = resp.json()
    assert D(data["current_value"]) == D("200000")
    assert data["value_updated_at"] is not None
    assert data["name"] == inv["name"]
    assert data["ticker"] == "AAPL"
    assert D(data["invested_amount"]) == D("150000")
    assert D(data["quantity"]) == D("10")


async def test_update_sin_cambiar_el_valor_no_pisa_value_updated_at(api_auth_client):
    inv = await create(api_auth_client, stock())
    resp = await api_auth_client.put(f"{URL}/{inv['id']}", json={"notes": "una nota"})
    assert resp.json()["value_updated_at"] == inv["value_updated_at"]
    same = await api_auth_client.put(f"{URL}/{inv['id']}", json={"current_value": "172500"})
    assert same.json()["value_updated_at"] == inv["value_updated_at"]


async def test_null_en_campo_obligatorio_se_ignora(api_auth_client):
    inv = await create(api_auth_client, stock())
    resp = await api_auth_client.put(
        f"{URL}/{inv['id']}",
        json={
            "name": None,
            "invested_amount": None,
            "currency": None,
            "asset_type": None,
            "status": None,
            "notify_maturity": None,
            "price_source": None,
            "institution": "Balanz",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["name"] == "Apple CEDEAR"
    assert D(data["invested_amount"]) == D("150000")
    assert data["currency"] == "ARS"
    assert data["asset_type"] == "stock"
    assert data["status"] == "active"
    assert data["notify_maturity"] is True
    assert data["price_source"] == "manual"
    assert data["institution"] == "Balanz"


async def test_null_en_campo_opcional_lo_borra(api_auth_client):
    inv = await create(api_auth_client, stock())
    resp = await api_auth_client.put(f"{URL}/{inv['id']}", json={"current_value": None})
    data = resp.json()
    assert data["current_value"] is None
    assert data["value_source"] == "invested"
    assert data["value_updated_at"] is None


async def test_cerrar_y_reabrir(api_auth_client):
    inv = await create(api_auth_client, stock())
    closed = (await api_auth_client.put(f"{URL}/{inv['id']}", json={"status": "closed"})).json()
    assert closed["status"] == "closed"
    assert (await api_auth_client.get(URL)).json() == []
    reopened = (await api_auth_client.put(f"{URL}/{inv['id']}", json={"status": "active"})).json()
    assert reopened["status"] == "active"
    assert len((await api_auth_client.get(URL)).json()) == 1


async def test_update_que_rompe_regla_cruzada_es_422_y_no_persiste(api_auth_client, db_session):
    inv = await create(api_auth_client, fixed_term())
    before = inv["maturity_date"]

    resp = await api_auth_client.put(
        f"{URL}/{inv['id']}", json={"maturity_date": "2000-01-01"}
    )
    assert resp.status_code == 422
    db_session.expire_all()
    row = (await db_session.execute(select(Investment).where(Investment.id == inv["id"]))).scalar_one()
    assert row.maturity_date.isoformat() == before


@pytest.mark.parametrize(
    "body",
    [{"interest_rate_tna": None}, {"currency": "EUR"}, {"start_date": None}, {"maturity_date": None}],
    ids=["borra-tna", "pasa-a-eur", "borra-inicio", "borra-vencimiento"],
)
async def test_update_que_deja_un_plazo_fijo_invalido_es_422(api_auth_client, body):
    inv = await create(api_auth_client, fixed_term())
    assert (await api_auth_client.put(f"{URL}/{inv['id']}", json=body)).status_code == 422


async def test_cambiar_el_tipo_a_plazo_fijo_valida_el_estado_resultante(api_auth_client):
    inv = await create(api_auth_client, stock(ticker=None))
    # Sin fechas ni TNA no puede pasar a plazo fijo...
    assert (
        await api_auth_client.put(f"{URL}/{inv['id']}", json={"asset_type": "fixed_term"})
    ).status_code == 422
    # ... y con todo en el mismo PUT, si.
    today = local_today(-180)
    ok = await api_auth_client.put(
        f"{URL}/{inv['id']}",
        json={
            "asset_type": "fixed_term",
            "interest_rate_tna": "40",
            "start_date": today.isoformat(),
            "maturity_date": (today + timedelta(days=30)).isoformat(),
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["fixed_term"]["term_days"] == 30


async def test_update_de_inexistente_es_404(api_auth_client):
    assert (await api_auth_client.put(f"{URL}/nada", json={"notes": "x"})).status_code == 404


async def test_delete(api_auth_client):
    inv = await create(api_auth_client, stock())
    assert (await api_auth_client.delete(f"{URL}/{inv['id']}")).status_code == 204
    assert (await api_auth_client.get(f"{URL}/{inv['id']}")).status_code == 404
    assert (await api_auth_client.delete(f"{URL}/{inv['id']}")).status_code == 404


async def test_cambiar_el_vencimiento_rehabilita_los_avisos(api_auth_client, db_session):
    inv = await create(api_auth_client, fixed_term())
    row = (await db_session.execute(select(Investment).where(Investment.id == inv["id"]))).scalar_one()
    row.eve_notice_for = row.maturity_date
    row.day_notice_for = row.maturity_date
    await db_session.commit()
    new_maturity = (row.maturity_date + timedelta(days=5)).isoformat()
    await api_auth_client.put(f"{URL}/{inv['id']}", json={"maturity_date": new_maturity})
    db_session.expire_all()
    row = (await db_session.execute(select(Investment).where(Investment.id == inv["id"]))).scalar_one()
    # Las marcas guardan el vencimiento viejo: ya no coinciden con el nuevo.
    assert row.eve_notice_for != row.maturity_date
    assert row.day_notice_for != row.maturity_date


# ── Resumen ─────────────────────────────────────────────────────────────────


async def _set_usd_rate(client, value="1450.50"):
    resp = await client.put("/api/v1/settings", json={"fx_usd_ars": value})
    assert resp.status_code == 200, resp.text


async def test_resumen_subtotales_por_moneda_y_totales(api_auth_client):
    await _set_usd_rate(api_auth_client)
    await create(api_auth_client, stock(name="Pesos", ticker=None, invested_amount="400000", current_value="500000"))
    await create(
        api_auth_client,
        stock(asset_type="fx", name="Dolares", ticker=None, currency="USD", invested_amount="1800", current_value="2000"),
    )
    data = (await api_auth_client.get(f"{URL}/summary")).json()
    by_cur = {c["currency"]: c for c in data["by_currency"]}
    assert D(by_cur["ARS"]["current_value"]) == D("500000.00")
    assert D(by_cur["ARS"]["invested"]) == D("400000.00")
    assert D(by_cur["ARS"]["gain"]) == D("100000.00")
    assert D(by_cur["USD"]["current_value"]) == D("2000.00")
    assert D(data["total_ars"]) == D("3401000.00")
    assert D(data["total_usd"]) == D("2344.71")
    assert data["missing_rates"] == []
    assert data["count_active"] == 2
    by_type = {t["asset_type"]: t for t in data["by_type"]}
    assert D(by_type["fx"]["value_ars"]) == D("2901000.00")
    assert by_type["stock"]["count"] == 1


async def test_resumen_sin_cotizacion_mantiene_los_subtotales(api_auth_client):
    await create(api_auth_client, stock(name="Pesos", ticker=None))
    await create(api_auth_client, stock(name="Dolares", ticker=None, currency="USD"))
    data = (await api_auth_client.get(f"{URL}/summary")).json()
    assert data["total_ars"] is None and data["total_usd"] is None
    assert data["missing_rates"] == ["USD"]
    assert {c["currency"] for c in data["by_currency"]} == {"ARS", "USD"}
    by_type = {t["asset_type"]: t for t in data["by_type"]}
    assert by_type["stock"]["value_ars"] is None


async def test_resumen_no_cuenta_cerradas(api_auth_client):
    a = await create(api_auth_client, stock(name="A", ticker=None))
    await create(api_auth_client, stock(name="B", ticker=None, current_value="1000"))
    await api_auth_client.put(f"{URL}/{a['id']}", json={"status": "closed"})
    data = (await api_auth_client.get(f"{URL}/summary")).json()
    assert data["count_active"] == 1
    assert D(data["total_ars"]) == D("1000.00")


async def test_resumen_proximos_vencimientos(api_auth_client):
    today = local_today(-180)
    for name, days in (("PF 45", 45), ("PF 10", 10), ("PF 3", 3), ("PF vencido", -2)):
        await create(
            api_auth_client,
            fixed_term(
                name=name,
                start_date=(today - timedelta(days=60)).isoformat(),
                maturity_date=(today + timedelta(days=days)).isoformat(),
            ),
        )
    data = (await api_auth_client.get(f"{URL}/summary", params={"tz_offset_minutes": -180})).json()
    upcoming = data["upcoming_maturities"]
    assert [u["name"] for u in upcoming] == ["PF 3", "PF 10"]
    assert [u["days_to_maturity"] for u in upcoming] == [3, 10]
    assert D(upcoming[0]["amount"]) > D("1000000")  # monto al vencimiento


async def test_resumen_limita_a_cinco_vencimientos(api_auth_client):
    today = local_today(-180)
    for n in range(7):
        await create(
            api_auth_client,
            fixed_term(
                name=f"PF {n}",
                start_date=(today - timedelta(days=5)).isoformat(),
                maturity_date=(today + timedelta(days=n + 1)).isoformat(),
            ),
        )
    data = (await api_auth_client.get(f"{URL}/summary", params={"tz_offset_minutes": -180})).json()
    assert len(data["upcoming_maturities"]) == 5
    assert data["upcoming_maturities"][0]["name"] == "PF 0"


async def test_resumen_vacio(api_auth_client):
    data = (await api_auth_client.get(f"{URL}/summary")).json()
    assert data["count_active"] == 0
    assert D(data["total_ars"]) == D("0.00")
    assert D(data["total_usd"]) == D("0.00")
    assert data["by_currency"] == [] and data["upcoming_maturities"] == []


# ── Aislamiento entre usuarios ──────────────────────────────────────────────


@pytest_asyncio.fixture
async def user_b(api_auth_client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/auth/api/register",
            json={
                "email": "userb@test.com",
                "full_name": "B",
                "password": "testpass123",
                "accept_terms": True,
            },
        )
        assert resp.status_code == 201, resp.text
        yield ac


async def test_otro_usuario_no_alcanza_la_inversion_ajena(api_auth_client, user_b):
    inv = await create(api_auth_client, stock())
    path = f"{URL}/{inv['id']}"
    assert (await user_b.get(path)).status_code == 404
    assert (await user_b.put(path, json={"name": "hackeada"})).status_code == 404
    assert (await user_b.put(path, json={"status": "closed"})).status_code == 404
    assert (await user_b.delete(path)).status_code == 404

    still = (await api_auth_client.get(path)).json()
    assert still["name"] == "Apple CEDEAR" and still["status"] == "active"


async def test_listas_y_resumen_son_por_usuario(api_auth_client, user_b):
    await create(api_auth_client, stock())
    assert (await user_b.get(URL)).json() == []
    assert (await user_b.get(URL, params={"status": "all"})).json() == []
    summary = (await user_b.get(f"{URL}/summary")).json()
    assert summary["count_active"] == 0 and summary["by_currency"] == []

"""Renovar un plazo fijo vencido: dos modos, interes como ingreso opcional,
idempotencia ante reintentos, historial y consistencia."""

from datetime import timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.clock import local_today
from app.main import app
from app.modules.inversiones import scheduler as investment_scheduler

pytestmark = pytest.mark.asyncio

URL = "/api/v1/finance/investments"
TX = "/api/v1/finance/transactions"


def D(value) -> Decimal:
    return Decimal(str(value))


def today():
    return local_today(-180)


def matured(**overrides):
    """1.000.000 al 30 % TNA por 30 dias: vencio hoy (cobra 1.024.657,53)."""
    t = today()
    body = {
        "asset_type": "fixed_term",
        "name": "Plazo fijo Galicia",
        "institution": "Galicia",
        "currency": "ARS",
        "invested_amount": "1000000",
        "interest_rate_tna": "30",
        "start_date": (t - timedelta(days=30)).isoformat(),
        "maturity_date": t.isoformat(),
        "timezone_offset_minutes": -180,
        "notes": "renovable",
    }
    body.update(overrides)
    return body


def renew_body(**overrides):
    body = {
        "mode": "principal_and_interest",
        "interest_rate_tna": "28",
        "term_days": 30,
        "timezone_offset_minutes": -180,
    }
    body.update(overrides)
    return body


async def create(client, body=None, expected=201):
    resp = await client.post(URL, json=body or matured())
    assert resp.status_code == expected, resp.text
    return resp.json()


async def renew(client, inv_id, expected=200, **overrides):
    resp = await client.post(f"{URL}/{inv_id}/renew", json=renew_body(**overrides))
    assert resp.status_code == expected, resp.text
    return resp.json()


@pytest_asyncio.fixture
async def user_b(client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/auth/api/register",
            json={
                "email": "userb@test.com",
                "full_name": "B",
                "password": "testpass123",
                "accept_terms": True,
                "confirm_age": True,
            },
        )
        assert resp.status_code == 201, resp.text
        yield ac


# ── Modos de renovacion ──────────────────────────────────────────────────────


async def test_renovar_capital_mas_interes(api_auth_client):
    inv = await create(api_auth_client)
    assert inv["can_renew"] is True
    data = await renew(api_auth_client, inv["id"])
    closed, new = data["closed"], data["renewed"]
    assert closed["status"] == "closed"
    assert D(closed["current_value"]) == D("1024657.53")
    assert closed["renewed_to_id"] == new["id"]
    assert closed["can_renew"] is False
    assert new["status"] == "active"
    assert new["asset_type"] == "fixed_term"
    assert D(new["invested_amount"]) == D("1024657.53")
    assert D(new["interest_rate_tna"]) == D("28")
    assert new["start_date"] == today().isoformat()
    assert new["maturity_date"] == (today() + timedelta(days=30)).isoformat()
    assert new["renewed_from_id"] == inv["id"]
    assert new["name"] == "Plazo fijo Galicia"
    assert new["institution"] == "Galicia"
    assert new["notes"] == "renovable"
    assert new["notify_maturity"] is True
    assert new["can_renew"] is False
    assert data["interest_transaction_id"] is None


async def test_renovar_solo_el_capital(api_auth_client):
    inv = await create(api_auth_client)
    data = await renew(api_auth_client, inv["id"], mode="principal_only")
    assert D(data["renewed"]["invested_amount"]) == D("1000000")
    assert data["closed"]["status"] == "closed"
    assert D(data["closed"]["current_value"]) == D("1024657.53")
    assert (await api_auth_client.get(TX)).json()["total"] == 0


async def test_renovar_con_el_monto_cobrado_editado(api_auth_client):
    inv = await create(api_auth_client)
    data = await renew(api_auth_client, inv["id"], amount_collected="1024600")
    assert D(data["closed"]["current_value"]) == D("1024600")
    assert D(data["renewed"]["invested_amount"]) == D("1024600")


async def test_renovar_por_fecha_de_vencimiento(api_auth_client):
    inv = await create(api_auth_client)
    maturity = (today() + timedelta(days=60)).isoformat()
    data = await renew(api_auth_client, inv["id"], term_days=None, maturity_date=maturity)
    assert data["renewed"]["maturity_date"] == maturity
    assert data["renewed"]["fixed_term"]["term_days"] == 60


async def test_renovar_vencido_hace_dias_con_inicio_de_hoy_o_del_vencimiento(api_auth_client):
    t = today()
    inv = await create(
        api_auth_client,
        matured(
            start_date=(t - timedelta(days=40)).isoformat(),
            maturity_date=(t - timedelta(days=10)).isoformat(),
        ),
    )
    # El banco acredito el dia del vencimiento: el nuevo puede arrancar ese dia.
    data = await renew(api_auth_client, inv["id"], start_date=(t - timedelta(days=10)).isoformat())
    assert data["renewed"]["start_date"] == (t - timedelta(days=10)).isoformat()


async def test_plazo_fijo_en_dolares(api_auth_client):
    inv = await create(api_auth_client, matured(currency="USD", invested_amount="1000"))
    data = await renew(api_auth_client, inv["id"])
    assert data["renewed"]["currency"] == "USD"
    assert D(data["renewed"]["invested_amount"]) == D("1024.66")


# ── Interes como ingreso ─────────────────────────────────────────────────────


async def test_registrar_el_interes_como_ingreso(api_auth_client):
    cat = (await api_auth_client.post("/api/v1/finance/categories", json={"name": "Intereses"})).json()["id"]
    acc = (
        await api_auth_client.post(
            "/api/v1/finance/accounts",
            json={"name": "Caja", "bank_name": "Galicia", "account_type": "savings", "last4": "9999"},
        )
    ).json()["id"]
    inv = await create(api_auth_client)
    data = await renew(
        api_auth_client,
        inv["id"],
        mode="principal_only",
        register_interest_income=True,
        income_category_id=cat,
        income_bank_account_id=acc,
    )
    tx_id = data["interest_transaction_id"]
    assert tx_id
    items = (await api_auth_client.get(TX)).json()["items"]
    assert len(items) == 1
    tx = items[0]
    assert tx["id"] == tx_id
    assert tx["type"] == "income"
    assert D(tx["amount"]) == D("24657.53")
    assert tx["product_name"] == "Interés plazo fijo: Plazo fijo Galicia"
    assert tx["transaction_date"] == today().isoformat()
    assert tx["category_id"] == cat
    assert tx["payment_method"] == "transfer"
    assert tx["bank_entity_name"] == "Galicia"
    assert tx["account_type"] == "savings"
    assert tx["is_recurring"] is False


async def test_sin_la_marca_no_se_crea_ingreso(api_auth_client):
    inv = await create(api_auth_client)
    data = await renew(api_auth_client, inv["id"], mode="principal_only", register_interest_income=False)
    assert data["interest_transaction_id"] is None
    assert (await api_auth_client.get(TX)).json()["total"] == 0


async def test_la_marca_se_ignora_si_se_reinvierte_el_interes(api_auth_client):
    inv = await create(api_auth_client)
    data = await renew(api_auth_client, inv["id"], register_interest_income=True)
    assert data["interest_transaction_id"] is None
    assert (await api_auth_client.get(TX)).json()["total"] == 0


async def test_categoria_o_cuenta_ajena_es_404_y_no_renueva(api_auth_client, user_b):
    cat_b = (await user_b.post("/api/v1/finance/categories", json={"name": "Ajena"})).json()["id"]
    acc_b = (await user_b.post("/api/v1/finance/accounts", json={"name": "B", "account_type": "cash"})).json()["id"]
    inv = await create(api_auth_client)
    await renew(api_auth_client, inv["id"], expected=404, mode="principal_only", register_interest_income=True, income_category_id=cat_b)
    await renew(api_auth_client, inv["id"], expected=404, mode="principal_only", register_interest_income=True, income_bank_account_id=acc_b)
    got = (await api_auth_client.get(f"{URL}/{inv['id']}")).json()
    assert got["status"] == "active" and got["renewed_to_id"] is None
    assert (await api_auth_client.get(URL)).json()[0]["id"] == inv["id"]


async def test_interes_negativo_en_solo_capital_es_422(api_auth_client):
    inv = await create(api_auth_client)
    await renew(api_auth_client, inv["id"], expected=422, mode="principal_only", amount_collected="999999")
    # en el limite exacto (interes 0) se acepta y no crea ingreso
    data = await renew(
        api_auth_client, inv["id"], mode="principal_only", amount_collected="1000000", register_interest_income=True
    )
    assert data["interest_transaction_id"] is None


# ── Precondiciones ───────────────────────────────────────────────────────────


async def test_no_vencido_es_422_y_no_cambia_nada(api_auth_client):
    t = today()
    inv = await create(api_auth_client, matured(maturity_date=(t + timedelta(days=1)).isoformat()))
    assert inv["can_renew"] is False
    await renew(api_auth_client, inv["id"], expected=422)
    got = (await api_auth_client.get(f"{URL}/{inv['id']}")).json()
    assert got["status"] == "active"
    assert (await api_auth_client.get(URL)).json().__len__() == 1


async def test_no_es_plazo_fijo_o_esta_cerrado_es_422(api_auth_client):
    stock = await create(
        api_auth_client,
        {"asset_type": "stock", "name": "Apple", "currency": "ARS", "invested_amount": "1000"},
    )
    await renew(api_auth_client, stock["id"], expected=422)
    inv = await create(api_auth_client)
    await api_auth_client.put(f"{URL}/{inv['id']}", json={"status": "closed"})
    await renew(api_auth_client, inv["id"], expected=422)


async def test_ajeno_es_404(api_auth_client, user_b):
    inv = await create(api_auth_client)
    await renew(user_b, inv["id"], expected=404)
    assert (await user_b.get(f"{URL}/{inv['id']}/renewals")).status_code == 404
    assert (await api_auth_client.get(f"{URL}/{inv['id']}")).json()["status"] == "active"


async def test_inexistente_es_404(api_auth_client):
    await renew(api_auth_client, "no-existe", expected=404)


async def test_doble_renovacion_da_409_y_deja_una_sola(api_auth_client):
    inv = await create(api_auth_client)
    await renew(api_auth_client, inv["id"])
    await renew(api_auth_client, inv["id"], expected=409)
    activos = (await api_auth_client.get(URL, params={"status": "all"})).json()
    assert len(activos) == 2


async def test_renovar_sin_autenticacion(client):
    resp = await client.post(f"{URL}/x/renew", json=renew_body())
    assert resp.status_code == 401


@pytest.mark.parametrize(
    "overrides",
    [
        {"start_date_offset": -31},  # antes del vencimiento anterior
        {"start_date_offset": 1},  # en el futuro
        {"term_days": 30, "maturity_offset": 45},  # plazo y fecha que no coinciden
        {"term_days": None},  # ni plazo ni fecha
        {"term_days": 0},
        {"term_days": 3651},
        {"interest_rate_tna": "0"},
        {"interest_rate_tna": "1000"},
        {"interest_rate_tna": "-1"},
        {"amount_collected": "10000000000"},
        {"amount_collected": "-5"},
        {"mode": "otro"},
        {"income_payment_method": "Efectivo", "mode": "principal_only", "register_interest_income": True},
        {"maturity_offset": 0},  # vencimiento igual al inicio
        {"maturity_date": "2101-01-01", "term_days": None},
    ],
)
async def test_valores_invalidos_son_422(api_auth_client, overrides):
    inv = await create(api_auth_client)
    t = today()
    overrides = dict(overrides)
    if "start_date_offset" in overrides:
        overrides["start_date"] = (t + timedelta(days=overrides.pop("start_date_offset"))).isoformat()
    if "maturity_offset" in overrides:
        overrides["maturity_date"] = (t + timedelta(days=overrides.pop("maturity_offset"))).isoformat()
    resp = await api_auth_client.post(f"{URL}/{inv['id']}/renew", json=renew_body(**overrides))
    assert resp.status_code == 422, resp.text
    assert (await api_auth_client.get(f"{URL}/{inv['id']}")).json()["status"] == "active"


# ── Historial y consistencia ─────────────────────────────────────────────────


async def test_historial_de_cuatro_tramos_desde_cualquiera(api_auth_client):
    t = today()
    first = await create(
        api_auth_client,
        matured(start_date=(t - timedelta(days=90)).isoformat(), maturity_date=(t - timedelta(days=60)).isoformat()),
    )
    ids = [first["id"]]
    # Tres renovaciones consecutivas, cada una vencida: se fabrican ajustando el
    # vencimiento del ultimo tramo antes de renovarlo.
    current = first
    for _ in range(3):
        new = (await renew(api_auth_client, current["id"], start_date=current["maturity_date"], term_days=10))["renewed"]
        ids.append(new["id"])
        past = (t - timedelta(days=0)).isoformat()
        await api_auth_client.put(f"{URL}/{new['id']}", json={"maturity_date": past, "start_date": (t - timedelta(days=30)).isoformat()})
        current = (await api_auth_client.get(f"{URL}/{new['id']}")).json()
    for probe in (ids[0], ids[2], ids[3]):
        resp = await api_auth_client.get(f"{URL}/{probe}/renewals")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert [i["id"] for i in data["items"]] == ids
        assert data["currency"] == "ARS"
        assert data["items"][0]["status"] == "closed"
        assert data["items"][-1]["status"] == "active"
        assert D(data["accumulated_interest"]) > 0
        assert data["items"][1]["renewed_from_id"] == ids[0]


async def test_historial_de_una_inversion_sin_renovar(api_auth_client):
    inv = await create(api_auth_client)
    data = (await api_auth_client.get(f"{URL}/{inv['id']}/renewals")).json()
    assert [i["id"] for i in data["items"]] == [inv["id"]]
    assert D(data["accumulated_interest"]) == 0
    assert D(data["items"][0]["interest"]) == D("24657.53")


async def test_historial_calcula_el_interes_cobrado(api_auth_client):
    inv = await create(api_auth_client)
    new = (await renew(api_auth_client, inv["id"]))["renewed"]
    data = (await api_auth_client.get(f"{URL}/{new['id']}/renewals")).json()
    assert D(data["accumulated_interest"]) == D("24657.53")
    assert D(data["items"][0]["interest"]) == D("24657.53")
    assert D(data["items"][0]["amount_at_maturity"]) == D("1024657.53")
    assert data["items"][0]["term_days"] == 30


async def test_reabrir_una_renovada_es_422(api_auth_client):
    inv = await create(api_auth_client)
    await renew(api_auth_client, inv["id"])
    resp = await api_auth_client.put(f"{URL}/{inv['id']}", json={"status": "active"})
    assert resp.status_code == 422
    assert (await api_auth_client.get(f"{URL}/{inv['id']}")).json()["status"] == "closed"
    # otros cambios (notas) siguen permitidos
    assert (await api_auth_client.put(f"{URL}/{inv['id']}", json={"notes": "x"})).status_code == 200


async def test_borrar_la_renovacion_deja_el_anterior_cerrado_y_reabrible(api_auth_client):
    inv = await create(api_auth_client)
    new = (await renew(api_auth_client, inv["id"]))["renewed"]
    assert (await api_auth_client.delete(f"{URL}/{new['id']}")).status_code == 204
    got = (await api_auth_client.get(f"{URL}/{inv['id']}")).json()
    assert got["status"] == "closed"
    assert got["renewed_to_id"] is None
    reopened = await api_auth_client.put(f"{URL}/{inv['id']}", json={"status": "active"})
    assert reopened.status_code == 200
    # y se puede volver a renovar
    await renew(api_auth_client, inv["id"])


async def test_borrar_el_anterior_deja_la_renovacion_sin_origen(api_auth_client):
    inv = await create(api_auth_client)
    new = (await renew(api_auth_client, inv["id"]))["renewed"]
    assert (await api_auth_client.delete(f"{URL}/{inv['id']}")).status_code == 204
    got = (await api_auth_client.get(f"{URL}/{new['id']}")).json()
    assert got["renewed_from_id"] is None
    assert (await api_auth_client.get(f"{URL}/{new['id']}/renewals")).json()["items"][0]["id"] == new["id"]


async def test_lista_trae_el_vinculo_de_renovacion(api_auth_client):
    inv = await create(api_auth_client)
    new = (await renew(api_auth_client, inv["id"]))["renewed"]
    rows = {r["id"]: r for r in (await api_auth_client.get(URL, params={"status": "all"})).json()}
    assert rows[inv["id"]]["renewed_to_id"] == new["id"]
    assert rows[new["id"]]["renewed_from_id"] == inv["id"]


async def test_avisos_de_vencimiento_solo_para_el_nuevo(api_auth_client, db_session, monkeypatch, engine):
    from datetime import datetime, timezone

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.modules.push.service import PushService

    monkeypatch.setattr(
        investment_scheduler,
        "AsyncSessionLocal",
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
    )
    sent = []

    async def fake_send(self, user_id, title, body, data=None):
        sent.append((title, data))

    monkeypatch.setattr(PushService, "send_to_user", fake_send)
    investment_scheduler._handled.clear()

    inv = await create(api_auth_client)
    new = (await renew(api_auth_client, inv["id"], term_days=2))["renewed"]
    # Dia del vencimiento del nuevo, 09:00 locales.
    day = today() + timedelta(days=2)
    await investment_scheduler._tick(datetime(day.year, day.month, day.day, 12, 0, tzinfo=timezone.utc))
    assert [d["investment_id"] for _, d in sent] == [new["id"]]
    investment_scheduler._handled.clear()

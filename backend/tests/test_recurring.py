"""API de movimientos recurrentes: alta, validaciones, vista previa, ciclo de
vida (pausar/editar/borrar) y pendientes de confirmacion.

El reloj se fija con la fixture `clock` (parchea `rules.utc_now`): hoy es
2026-10-25 12:00 local (15:00 UTC, offset -180).
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.recurrentes import rules

pytestmark = pytest.mark.asyncio

BASE = "/api/v1/finance/recurring"
TX = "/api/v1/finance/transactions"
NOW = datetime(2026, 10, 25, 15, 0, tzinfo=timezone.utc)


@pytest.fixture
def clock(monkeypatch):
    state = {"now": NOW}
    monkeypatch.setattr(rules, "utc_now", lambda: state["now"])
    return state


def D(value) -> Decimal:
    return Decimal(str(value))


def salary(**overrides):
    body = {
        "type": "income",
        "name": "Sueldo",
        "amount": "850000",
        "frequency": "monthly",
        "day_of_month": 5,
        "start_date": "2026-11-01",
        "timezone_offset_minutes": -180,
    }
    body.update(overrides)
    return body


async def create(client, body, expected=201):
    resp = await client.post(BASE, json=body)
    assert resp.status_code == expected, resp.text
    return resp.json()


async def transactions(client, **params):
    resp = await client.get(TX, params={"limit": 200, **params})
    assert resp.status_code == 200, resp.text
    return resp.json()["items"]


@pytest_asyncio.fixture
async def user_b(client):
    """Otro usuario con su propio cliente (cookies separadas)."""
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


# ── Alta ─────────────────────────────────────────────────────────────────────


async def test_crear_sueldo_mensual(api_auth_client, clock):
    data = await create(api_auth_client, salary())
    assert data["next_occurrence_date"] == "2026-11-05"
    assert data["anchor_date"] == "2026-11-05"
    assert data["rule_label"] == "Todos los meses el día 5"
    assert data["state"] == "active"
    assert data["status"] == "active"
    assert D(data["amount"]) == D("850000")
    assert data["pending_count"] == 0
    assert data["last_amount"] is None
    # No vence hoy: no genera nada todavia.
    assert await transactions(api_auth_client) == []


async def test_requiere_autenticacion(client):
    assert (await client.get(BASE)).status_code == 401
    assert (await client.post(BASE, json=salary())).status_code == 401


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": "0"},
        {"amount": "-5"},
        {"amount": "10000000000"},
        {"payment_method": "Efectivo"},
        {"account_type": "billetera"},
        {"type": "transfer"},
        {"merchant_category": "otra"},
        {"currency": "EUR"},
        {"end_date": "2026-10-01"},
        {"name": "   "},
        {"interval_count": 13},
        {"interval_count": 0},
        {"day_of_month": 32},
        {"day_of_month": None},
        {"start_date": "1969-12-31"},
        {"start_date": "2101-01-01"},
        {"timezone_offset_minutes": 900},
        {"frequency": "hourly"},
    ],
)
async def test_valores_invalidos_son_422(api_auth_client, clock, overrides):
    body = salary()
    body.update(overrides)
    await create(api_auth_client, body, expected=422)


async def test_regla_incompleta_es_422(api_auth_client, clock):
    await create(
        api_auth_client,
        {"type": "expense", "name": "Gimnasio", "amount": "100", "frequency": "weekly", "start_date": "2026-11-01"},
        expected=422,
    )
    await create(
        api_auth_client,
        {"type": "expense", "name": "Seguro", "amount": "100", "frequency": "yearly", "day_of_month": 5, "start_date": "2026-11-01"},
        expected=422,
    )


async def test_monto_en_el_limite_se_acepta(api_auth_client, clock):
    data = await create(api_auth_client, salary(amount="9999999999.99"))
    assert D(data["amount"]) == D("9999999999.99")


async def test_sin_monto_solo_con_confirmacion(api_auth_client, clock):
    body = salary(name="Luz", type="expense", requires_confirmation=True)
    del body["amount"]
    data = await create(api_auth_client, body)
    assert data["amount"] is None
    body["requires_confirmation"] = False
    await create(api_auth_client, body, expected=422)


async def test_campos_de_regla_ajenos_se_guardan_en_null(api_auth_client, clock):
    data = await create(
        api_auth_client,
        salary(frequency="weekly", weekday=0, day_of_month=5, month_of_year=3),
    )
    assert data["weekday"] == 0
    assert data["day_of_month"] is None
    assert data["month_of_year"] is None
    assert data["rule_label"] == "Todas las semanas los lunes"


async def test_categoria_o_cuenta_ajena_es_404(api_auth_client, user_b, clock):
    cat_b = (await user_b.post("/api/v1/finance/categories", json={"name": "Ajena"})).json()["id"]
    acc_b = (
        await user_b.post(
            "/api/v1/finance/accounts",
            json={"name": "Cuenta B", "account_type": "checking"},
        )
    ).json()["id"]
    await create(api_auth_client, salary(category_id=cat_b), expected=404)
    await create(api_auth_client, salary(bank_account_id=acc_b), expected=404)
    await create(api_auth_client, salary(category_id="no-existe"), expected=404)
    assert (await api_auth_client.get(BASE)).json() == []


async def test_actualizar_con_categoria_ajena_es_404(api_auth_client, user_b, clock):
    cat_b = (await user_b.post("/api/v1/finance/categories", json={"name": "Ajena"})).json()["id"]
    rec = await create(api_auth_client, salary())
    resp = await api_auth_client.put(f"{BASE}/{rec['id']}", json={"category_id": cat_b})
    assert resp.status_code == 404


async def test_creada_el_dia_que_toca_genera_en_el_request(api_auth_client, clock):
    cat = (await api_auth_client.post("/api/v1/finance/categories", json={"name": "Ingresos"})).json()["id"]
    acc = (
        await api_auth_client.post(
            "/api/v1/finance/accounts",
            json={"name": "Galicia", "bank_name": "Banco Galicia", "account_type": "checking", "last4": "1234"},
        )
    ).json()["id"]
    data = await create(
        api_auth_client,
        salary(
            start_date="2026-10-25",
            day_of_month=25,
            category_id=cat,
            bank_account_id=acc,
            payment_method="transfer",
            description="Sueldo mensual",
            notes="neto",
            merchant_name="Empresa SA",
        ),
    )
    items = await transactions(api_auth_client)
    assert len(items) == 1
    tx = items[0]
    assert tx["transaction_date"] == "2026-10-25"
    assert tx["type"] == "income"
    assert D(tx["amount"]) == D("850000")
    assert tx["product_name"] == "Sueldo"
    assert tx["product_description"] == "Sueldo mensual"
    assert tx["notes"] == "neto"
    assert tx["category_id"] == cat
    assert tx["payment_method"] == "transfer"
    assert tx["merchant_name"] == "Empresa SA"
    assert tx["bank_entity_name"] == "Banco Galicia"
    assert tx["account_type"] == "checking"
    assert tx["account_last4"] == "1234"
    assert tx["is_recurring"] is True
    assert tx["recurrence_id"] == data["id"]
    # El cursor ya apunta a la proxima.
    got = (await api_auth_client.get(f"{BASE}/{data['id']}")).json()
    assert got["next_occurrence_date"] == "2026-11-25"
    assert got["last_occurrence_date"] == "2026-10-25"
    assert D(got["last_amount"]) == D("850000")


async def test_inicio_pasado_sin_registrar_las_anteriores(api_auth_client, clock):
    data = await create(api_auth_client, salary(start_date="2026-07-01", day_of_month=1))
    assert data["next_occurrence_date"] == "2026-11-01"
    assert await transactions(api_auth_client) == []


async def test_inicio_pasado_registrando_las_anteriores(api_auth_client, clock):
    data = await create(
        api_auth_client, salary(start_date="2026-07-01", day_of_month=1, generate_past=True)
    )
    items = await transactions(api_auth_client)
    assert sorted(t["transaction_date"] for t in items) == [
        "2026-07-01",
        "2026-08-01",
        "2026-09-01",
        "2026-10-01",
    ]
    assert {t["recurrence_id"] for t in items} == {data["id"]}
    assert data["next_occurrence_date"] == "2026-11-01"


async def test_registrar_las_anteriores_mas_de_120_es_422(api_auth_client, clock):
    resp = await api_auth_client.post(
        BASE,
        json=salary(frequency="daily", day_of_month=None, start_date="2026-05-01", generate_past=True),
    )
    assert resp.status_code == 422
    assert "120" in resp.text
    assert (await api_auth_client.get(BASE)).json() == []


async def test_registrar_las_anteriores_con_inicio_de_mas_de_un_anio_es_422(api_auth_client, clock):
    await create(
        api_auth_client,
        salary(start_date="2025-01-01", day_of_month=1, frequency="yearly", month_of_year=1, generate_past=True),
        expected=422,
    )


async def test_exactamente_120_anteriores_se_acepta(api_auth_client, clock):
    # 120 dias hacia atras + hoy => 121 fechas diarias: tope exacto un dia despues.
    await create(
        api_auth_client,
        salary(frequency="daily", day_of_month=None, start_date="2026-06-27", generate_past=True),
        expected=422,
    )
    data = await create(
        api_auth_client,
        salary(frequency="daily", day_of_month=None, start_date="2026-06-28", generate_past=True),
    )
    assert len(await transactions(api_auth_client)) == 120
    assert data["next_occurrence_date"] == "2026-10-26"


async def test_fin_anterior_a_la_primera_ocurrencia_queda_finalizada(api_auth_client, clock):
    data = await create(api_auth_client, salary(start_date="2026-10-26", end_date="2026-10-30"))
    assert data["next_occurrence_date"] is None
    assert data["state"] == "finished"


# ── Vista previa y proximos ──────────────────────────────────────────────────


async def test_preview_no_persiste_y_calcula_5_fechas(api_auth_client, clock):
    resp = await api_auth_client.post(
        f"{BASE}/preview",
        json={"frequency": "monthly", "day_of_month": 31, "start_date": "2027-01-31", "tz_offset_minutes": -180},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["anchor_date"] == "2027-01-31"
    assert data["dates"] == ["2027-01-31", "2027-02-28", "2027-03-31", "2027-04-30", "2027-05-31"]
    assert (await api_auth_client.get(BASE)).json() == []


async def test_preview_bimestral_desde_hoy(api_auth_client, clock):
    resp = await api_auth_client.post(
        f"{BASE}/preview",
        json={"frequency": "monthly", "interval_count": 2, "day_of_month": 5, "start_date": "2026-10-25"},
    )
    assert resp.json()["dates"][:3] == ["2026-11-05", "2027-01-05", "2027-03-05"]


async def test_preview_respeta_fin_y_valida(api_auth_client, clock):
    resp = await api_auth_client.post(
        f"{BASE}/preview",
        json={"frequency": "monthly", "day_of_month": 5, "start_date": "2026-11-01", "end_date": "2027-01-10"},
    )
    assert resp.json()["dates"] == ["2026-11-05", "2026-12-05", "2027-01-05"]
    bad = await api_auth_client.post(f"{BASE}/preview", json={"frequency": "weekly", "start_date": "2026-11-01"})
    assert bad.status_code == 422


async def test_upcoming_lista_sueldo_y_alquiler_con_totales(api_auth_client, clock):
    await create(api_auth_client, salary())
    await create(
        api_auth_client,
        salary(type="expense", name="Alquiler", amount="300000", day_of_month=10),
    )
    await create(api_auth_client, salary(name="Pausada", day_of_month=7))
    pausada = (await api_auth_client.get(BASE)).json()
    pausada_id = next(r["id"] for r in pausada if r["name"] == "Pausada")
    await api_auth_client.post(f"{BASE}/{pausada_id}/pause", json={})
    resp = await api_auth_client.get(f"{BASE}/upcoming", params={"days": 30, "tz_offset_minutes": -180})
    assert resp.status_code == 200
    data = resp.json()
    assert [(i["date"], i["name"], i["type"]) for i in data["items"]] == [
        ("2026-11-05", "Sueldo", "income"),
        ("2026-11-10", "Alquiler", "expense"),
    ]
    totals = {(t["type"], t["currency"]): D(t["total"]) for t in data["totals"]}
    assert totals == {("income", "ARS"): D("850000"), ("expense", "ARS"): D("300000")}


async def test_upcoming_valida_el_rango_de_dias(api_auth_client, clock):
    assert (await api_auth_client.get(f"{BASE}/upcoming", params={"days": 0})).status_code == 422
    assert (await api_auth_client.get(f"{BASE}/upcoming", params={"days": 91})).status_code == 422
    assert (await api_auth_client.get(f"{BASE}/upcoming")).status_code == 200


# ── Lectura ──────────────────────────────────────────────────────────────────


async def test_lista_detalle_y_filtro_por_estado(api_auth_client, clock):
    a = await create(api_auth_client, salary(name="B sueldo"))
    b = await create(api_auth_client, salary(name="A alquiler", type="expense", day_of_month=2))
    await api_auth_client.post(f"{BASE}/{a['id']}/pause", json={})
    all_items = (await api_auth_client.get(BASE)).json()
    # Activas primero.
    assert [r["name"] for r in all_items] == ["A alquiler", "B sueldo"]
    assert [r["id"] for r in (await api_auth_client.get(BASE, params={"status": "paused"})).json()] == [a["id"]]
    assert [r["id"] for r in (await api_auth_client.get(BASE, params={"status": "active"})).json()] == [b["id"]]
    detail = (await api_auth_client.get(f"{BASE}/{b['id']}")).json()
    assert detail["next_dates"][:3] == ["2026-11-02", "2026-12-02", "2027-01-02"]
    assert detail["recent_occurrences"] == []
    assert (await api_auth_client.get(f"{BASE}/no-existe")).status_code == 404


# ── Pausar / reanudar ────────────────────────────────────────────────────────


async def test_pausar_y_reanudar_no_genera_lo_pausado(api_auth_client, clock):
    rec = await create(api_auth_client, salary())
    paused = (await api_auth_client.post(f"{BASE}/{rec['id']}/pause", json={"timezone_offset_minutes": -180})).json()
    assert paused["state"] == "paused"
    assert paused["paused_at"] is not None
    # Pausar de nuevo es idempotente.
    assert (await api_auth_client.post(f"{BASE}/{rec['id']}/pause", json={})).status_code == 200

    clock["now"] = datetime(2026, 12, 10, 15, 0, tzinfo=timezone.utc)
    resumed = (await api_auth_client.post(f"{BASE}/{rec['id']}/resume", json={})).json()
    assert resumed["state"] == "active"
    assert resumed["paused_at"] is None
    # Ni el 5/11 ni el 5/12 se generan; sigue el 5/1.
    assert resumed["next_occurrence_date"] == "2027-01-05"
    assert await transactions(api_auth_client) == []


async def test_reanudar_el_dia_que_toca_genera_en_el_acto(api_auth_client, clock):
    rec = await create(api_auth_client, salary(start_date="2026-10-26", day_of_month=26))
    await api_auth_client.post(f"{BASE}/{rec['id']}/pause", json={})
    clock["now"] = datetime(2026, 11, 26, 15, 0, tzinfo=timezone.utc)
    resumed = (await api_auth_client.post(f"{BASE}/{rec['id']}/resume", json={})).json()
    assert resumed["next_occurrence_date"] == "2026-12-26"
    items = await transactions(api_auth_client)
    assert [t["transaction_date"] for t in items] == ["2026-11-26"]


# ── Edicion ──────────────────────────────────────────────────────────────────


async def test_editar_el_monto_no_toca_lo_generado(api_auth_client, clock):
    rec = await create(api_auth_client, salary(start_date="2026-10-25", day_of_month=25))
    clock["now"] = datetime(2026, 11, 25, 15, 0, tzinfo=timezone.utc)
    resp = await api_auth_client.put(f"{BASE}/{rec['id']}", json={"amount": "900000"})
    assert resp.status_code == 200
    assert D(resp.json()["amount"]) == D("900000")
    # El del 25/10 sigue en 850.000; el de hoy (25/11) ya sale con el monto nuevo.
    amounts = sorted((t["transaction_date"], D(t["amount"])) for t in await transactions(api_auth_client))
    assert amounts == [("2026-10-25", D("850000")), ("2026-11-25", D("900000"))]


async def test_cambiar_la_regla_recalcula_el_ancla_hacia_adelante(api_auth_client, clock):
    rec = await create(api_auth_client, salary(start_date="2026-10-25", day_of_month=25))
    # Hoy es 25/10 y ya se registro el del 25; pasar al 28 genera el de este mes.
    resp = await api_auth_client.put(f"{BASE}/{rec['id']}", json={"day_of_month": 28})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["anchor_date"] == "2026-10-28"
    assert data["next_occurrence_date"] == "2026-10-28"
    assert data["rule_label"] == "Todos los meses el día 28"
    # Pasar a semanal limpia los campos que no corresponden.
    data = (await api_auth_client.put(f"{BASE}/{rec['id']}", json={"frequency": "weekly", "weekday": 0})).json()
    assert data["day_of_month"] is None
    assert data["weekday"] == 0
    assert data["next_occurrence_date"] == "2026-10-26"


async def test_editar_regla_invalida_es_422_y_no_cambia_nada(api_auth_client, clock):
    rec = await create(api_auth_client, salary())
    assert (await api_auth_client.put(f"{BASE}/{rec['id']}", json={"frequency": "weekly"})).status_code == 422
    assert (await api_auth_client.put(f"{BASE}/{rec['id']}", json={"amount": "0"})).status_code == 422
    assert (await api_auth_client.put(f"{BASE}/{rec['id']}", json={"end_date": "2026-01-01"})).status_code == 422
    same = (await api_auth_client.get(f"{BASE}/{rec['id']}")).json()
    assert same["frequency"] == "monthly"
    assert D(same["amount"]) == D("850000")


async def test_null_en_campo_obligatorio_se_ignora_y_en_opcional_se_borra(api_auth_client, clock):
    rec = await create(api_auth_client, salary(notes="nota", description="desc"))
    resp = await api_auth_client.put(f"{BASE}/{rec['id']}", json={"name": None, "notes": None, "type": None})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["name"] == "Sueldo"
    assert data["type"] == "income"
    assert data["notes"] is None
    assert data["description"] == "desc"


async def test_fin_de_la_regla_finaliza_y_se_puede_revivir(api_auth_client, clock):
    rec = await create(api_auth_client, salary(start_date="2026-10-01", day_of_month=1))
    assert rec["next_occurrence_date"] == "2026-11-01"
    done = (await api_auth_client.put(f"{BASE}/{rec['id']}", json={"end_date": "2026-10-31"})).json()
    assert done["state"] == "finished"
    assert done["next_occurrence_date"] is None
    revived = (await api_auth_client.put(f"{BASE}/{rec['id']}", json={"end_date": "2027-03-31"})).json()
    assert revived["state"] == "active"
    assert revived["next_occurrence_date"] == "2026-11-01"


# ── Borrado y vinculos ───────────────────────────────────────────────────────


async def test_borrar_la_plantilla_conserva_las_transacciones(api_auth_client, clock):
    rec = await create(api_auth_client, salary(start_date="2026-10-25", day_of_month=25))
    resp = await api_auth_client.delete(f"{BASE}/{rec['id']}")
    assert resp.status_code == 204
    assert (await api_auth_client.get(f"{BASE}/{rec['id']}")).status_code == 404
    items = await transactions(api_auth_client)
    assert len(items) == 1
    assert items[0]["is_recurring"] is True
    assert items[0]["recurrence_id"] is None


async def test_borrar_la_transaccion_generada_no_la_regenera(api_auth_client, clock):
    rec = await create(api_auth_client, salary(start_date="2026-10-25", day_of_month=25))
    tx = (await transactions(api_auth_client))[0]
    assert (await api_auth_client.delete(f"{TX}/{tx['id']}")).status_code == 204
    # Un "re-procesamiento" del mismo dia no la vuelve a crear: la ocurrencia sigue registrada.
    await api_auth_client.put(f"{BASE}/{rec['id']}", json={"notes": "x"})
    assert await transactions(api_auth_client) == []


async def test_filtro_por_recurrence_id_y_campo_en_manuales(api_auth_client, clock):
    a = await create(api_auth_client, salary(start_date="2026-10-25", day_of_month=25))
    await create(api_auth_client, salary(name="Otra", start_date="2026-10-25", day_of_month=25))
    manual = await api_auth_client.post(
        TX,
        json={
            "amount": "10",
            "type": "expense",
            "transaction_date": "2026-10-20",
            "account_type": "cash",
            "payment_method": "cash",
            "product_name": "Cafe",
        },
    )
    assert manual.json()["recurrence_id"] is None
    assert manual.json()["is_recurring"] is False
    resp = await api_auth_client.get(TX, params={"recurrence_id": a["id"]})
    body = resp.json()
    assert body["total"] == 1
    assert [t["product_name"] for t in body["items"]] == ["Sueldo"]
    assert (await api_auth_client.get(TX)).json()["total"] == 3


async def test_borrar_categoria_o_cuenta_usada_desvincula(api_auth_client, clock):
    cat = (await api_auth_client.post("/api/v1/finance/categories", json={"name": "Servicios"})).json()["id"]
    acc = (
        await api_auth_client.post(
            "/api/v1/finance/accounts", json={"name": "Efectivo", "account_type": "cash"}
        )
    ).json()["id"]
    rec = await create(api_auth_client, salary(category_id=cat, bank_account_id=acc))
    assert (await api_auth_client.delete(f"/api/v1/finance/categories/{cat}")).status_code == 204
    assert (await api_auth_client.delete(f"/api/v1/finance/accounts/{acc}")).status_code == 204
    got = (await api_auth_client.get(f"{BASE}/{rec['id']}")).json()
    assert got["category_id"] is None
    assert got["bank_account_id"] is None


async def test_la_generacion_sigue_si_la_categoria_ya_no_existe(api_auth_client, clock, db_session):
    """Defensivo: una categoria borrada a espaldas de la plantilla no frena la generacion."""
    from sqlalchemy import update

    from app.modules.recurrentes.models import RecurringTransaction

    cat = (await api_auth_client.post("/api/v1/finance/categories", json={"name": "Servicios"})).json()["id"]
    rec = await create(api_auth_client, salary(category_id=cat))
    await api_auth_client.delete(f"/api/v1/finance/categories/{cat}")
    await db_session.execute(
        update(RecurringTransaction).where(RecurringTransaction.id == rec["id"]).values(category_id=cat)
    )
    await db_session.commit()
    clock["now"] = datetime(2026, 11, 5, 15, 0, tzinfo=timezone.utc)
    resp = await api_auth_client.put(f"{BASE}/{rec['id']}", json={"notes": "hoy"})
    assert resp.status_code == 200
    items = await transactions(api_auth_client)
    assert len(items) == 1 and items[0]["category_id"] is None


# ── Pendientes (monto variable) ──────────────────────────────────────────────


def luz(**overrides):
    return salary(
        name="Luz",
        type="expense",
        amount="25000",
        requires_confirmation=True,
        start_date="2026-10-25",
        day_of_month=25,
        **overrides,
    )


async def test_pendiente_sin_crear_transaccion_ni_afectar_balance(api_auth_client, clock):
    rec = await create(api_auth_client, luz())
    assert rec["pending_count"] == 1
    assert await transactions(api_auth_client) == []
    pending = (await api_auth_client.get(f"{BASE}/occurrences")).json()
    assert len(pending) == 1
    p = pending[0]
    assert p["status"] == "pending"
    assert D(p["suggested_amount"]) == D("25000")
    assert p["occurrence_date"] == "2026-10-25"
    assert p["name"] == "Luz" and p["type"] == "expense"
    assert p["transaction_id"] is None
    # No suma al balance ni a los reportes.
    stats = (await api_auth_client.get("/api/v1/finance/summary")).json()
    assert D(stats["total_expenses"]) == 0


async def test_confirmar_con_monto_editado_crea_la_transaccion(api_auth_client, clock):
    await create(api_auth_client, luz())
    occ = (await api_auth_client.get(f"{BASE}/occurrences")).json()[0]
    resp = await api_auth_client.post(
        f"{BASE}/occurrences/{occ['id']}/confirm",
        json={"amount": "31250.50", "timezone_offset_minutes": -180},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "confirmed"
    assert data["transaction"]["transaction_date"] == "2026-10-25"
    assert D(data["transaction"]["amount"]) == D("31250.50")
    assert data["transaction"]["is_recurring"] is True
    items = await transactions(api_auth_client)
    assert len(items) == 1 and D(items[0]["amount"]) == D("31250.50")
    assert (await api_auth_client.get(f"{BASE}/occurrences")).json() == []


async def test_confirmar_dos_veces_deja_una_sola_transaccion(api_auth_client, clock):
    await create(api_auth_client, luz())
    occ = (await api_auth_client.get(f"{BASE}/occurrences")).json()[0]
    url = f"{BASE}/occurrences/{occ['id']}/confirm"
    first = await api_auth_client.post(url, json={"amount": "100"})
    second = await api_auth_client.post(url, json={"amount": "100"})
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["transaction_id"] == second.json()["transaction_id"]
    assert len(await transactions(api_auth_client)) == 1


async def test_confirmar_con_fecha_y_notas(api_auth_client, clock):
    await create(api_auth_client, luz())
    occ = (await api_auth_client.get(f"{BASE}/occurrences")).json()[0]
    resp = await api_auth_client.post(
        f"{BASE}/occurrences/{occ['id']}/confirm",
        json={"amount": "100", "transaction_date": "2026-10-20", "notes": "pagada antes"},
    )
    tx = resp.json()["transaction"]
    assert tx["transaction_date"] == "2026-10-20"
    assert tx["notes"] == "pagada antes"


async def test_saltear_y_confirmar_despues_da_409(api_auth_client, clock):
    await create(api_auth_client, luz())
    occ = (await api_auth_client.get(f"{BASE}/occurrences")).json()[0]
    skipped = await api_auth_client.post(f"{BASE}/occurrences/{occ['id']}/skip", json={})
    assert skipped.status_code == 200
    assert skipped.json()["status"] == "skipped"
    # Saltear de nuevo es idempotente.
    assert (await api_auth_client.post(f"{BASE}/occurrences/{occ['id']}/skip", json={})).status_code == 200
    again = await api_auth_client.post(f"{BASE}/occurrences/{occ['id']}/confirm", json={"amount": "1"})
    assert again.status_code == 409
    assert await transactions(api_auth_client) == []


async def test_saltear_una_confirmada_da_409(api_auth_client, clock):
    await create(api_auth_client, luz())
    occ = (await api_auth_client.get(f"{BASE}/occurrences")).json()[0]
    await api_auth_client.post(f"{BASE}/occurrences/{occ['id']}/confirm", json={"amount": "5"})
    assert (await api_auth_client.post(f"{BASE}/occurrences/{occ['id']}/skip", json={})).status_code == 409


async def test_confirmar_valida_el_monto(api_auth_client, clock):
    await create(api_auth_client, luz())
    occ = (await api_auth_client.get(f"{BASE}/occurrences")).json()[0]
    url = f"{BASE}/occurrences/{occ['id']}/confirm"
    assert (await api_auth_client.post(url, json={"amount": "0"})).status_code == 422
    assert (await api_auth_client.post(url, json={"amount": "10000000000"})).status_code == 422
    assert (await api_auth_client.post(url, json={})).status_code == 422
    assert (await api_auth_client.post(f"{BASE}/occurrences/no-existe/confirm", json={"amount": "1"})).status_code == 404


async def test_el_siguiente_pendiente_sugiere_el_ultimo_confirmado(api_auth_client, clock):
    rec = await create(api_auth_client, luz())
    occ = (await api_auth_client.get(f"{BASE}/occurrences")).json()[0]
    await api_auth_client.post(f"{BASE}/occurrences/{occ['id']}/confirm", json={"amount": "31250.50"})
    clock["now"] = datetime(2026, 11, 25, 15, 0, tzinfo=timezone.utc)
    # Un cambio de regla/edicion dispara la materializacion de lo vencido (sin push).
    await api_auth_client.put(f"{BASE}/{rec['id']}", json={"notes": "x"})
    nuevo = (await api_auth_client.get(f"{BASE}/occurrences")).json()
    assert len(nuevo) == 1
    assert nuevo[0]["occurrence_date"] == "2026-11-25"
    assert D(nuevo[0]["suggested_amount"]) == D("31250.50")


async def test_pendiente_sin_estimado_sugiere_null(api_auth_client, clock):
    body = luz()
    del body["amount"]
    await create(api_auth_client, body)
    occ = (await api_auth_client.get(f"{BASE}/occurrences")).json()[0]
    assert occ["suggested_amount"] is None


async def test_borrar_la_plantilla_borra_sus_pendientes(api_auth_client, clock):
    rec = await create(api_auth_client, luz())
    await api_auth_client.delete(f"{BASE}/{rec['id']}")
    assert (await api_auth_client.get(f"{BASE}/occurrences")).json() == []
    assert (await api_auth_client.get(f"{BASE}/occurrences", params={"status": "all"})).json() == []


async def test_detalle_muestra_las_ocurrencias_recientes(api_auth_client, clock):
    rec = await create(api_auth_client, salary(start_date="2026-10-25", day_of_month=25))
    detail = (await api_auth_client.get(f"{BASE}/{rec['id']}")).json()
    assert [o["status"] for o in detail["recent_occurrences"]] == ["generated"]
    assert detail["recent_occurrences"][0]["occurrence_date"] == "2026-10-25"


# ── Regresiones encontradas en la verificación contra Postgres ──────────────


async def test_reanudar_el_mismo_dia_que_ya_se_registro_no_rompe_ni_duplica(api_auth_client, clock):
    """Pausar y reanudar el mismo dia en que ya se genero la ocurrencia de hoy:
    el cursor no puede volver a hoy (daba 500 por la restriccion unica)."""
    rec = await create(api_auth_client, salary(start_date="2026-10-25", day_of_month=25))
    assert len(await transactions(api_auth_client)) == 1
    await api_auth_client.post(f"{BASE}/{rec['id']}/pause", json={})
    resp = await api_auth_client.post(f"{BASE}/{rec['id']}/resume", json={})
    assert resp.status_code == 200, resp.text
    assert resp.json()["next_occurrence_date"] == "2026-11-25"
    assert len(await transactions(api_auth_client)) == 1


async def test_cursor_apuntando_a_un_dia_ya_registrado_se_corrige_solo(api_auth_client, clock, db_session):
    from datetime import date

    from sqlalchemy import update

    from app.modules.recurrentes.models import RecurringTransaction

    rec = await create(api_auth_client, salary(start_date="2026-10-25", day_of_month=25))
    await db_session.execute(
        update(RecurringTransaction)
        .where(RecurringTransaction.id == rec["id"])
        .values(next_occurrence_date=date(2026, 10, 25))
    )
    await db_session.commit()
    resp = await api_auth_client.put(f"{BASE}/{rec['id']}", json={"notes": "x"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["next_occurrence_date"] == "2026-11-25"
    assert len(await transactions(api_auth_client)) == 1

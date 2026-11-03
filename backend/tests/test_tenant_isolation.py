import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app

pytestmark = pytest.mark.asyncio


async def _register(client: AsyncClient, email: str) -> None:
    resp = await client.post("/auth/api/register", json={
        "email": email,
        "full_name": "Test",
        "password": "testpass123",
        "accept_terms": True,
        "confirm_age": True,
    })
    assert resp.status_code == 201, resp.text


@pytest_asyncio.fixture
async def user_a(client):
    await _register(client, "usera@test.com")
    return client


@pytest_asyncio.fixture
async def user_b(user_a):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await _register(ac, "userb@test.com")
        yield ac


# Cada entrada crea un recurso como user_a y define los endpoints de detalle
# (GET/PATCH/PUT/DELETE) que user_b debe recibir como 404 al intentar usarlos.
RESOURCES = [
    {
        "name": "task",
        "create": ("POST", "/api/v1/tasks", {"title": "Tarea A"}),
        "detail": [
            ("PATCH", "{id}", {"title": "hackeada"}),
            ("DELETE", "{id}", None),
        ],
        "path": "/api/v1/tasks/{id}",
    },
    {
        "name": "transaction",
        "create": ("POST", "/api/v1/finance/transactions", {
            "amount": "100.00",
            "type": "expense",
            "transaction_date": "2026-01-01",
            "account_type": "cash",
            "payment_method": "cash",
            "product_name": "Producto A",
        }),
        "detail": [
            ("PUT", "{id}", {"amount": "999.00"}),
            ("DELETE", "{id}", None),
        ],
        "path": "/api/v1/finance/transactions/{id}",
    },
    {
        "name": "category",
        "create": ("POST", "/api/v1/finance/categories", {"name": "Categoria A"}),
        "detail": [
            ("PUT", "{id}", {"name": "hackeada"}),
            ("DELETE", "{id}", None),
        ],
        "path": "/api/v1/finance/categories/{id}",
    },
    {
        "name": "workout session",
        "create": ("POST", "/api/v1/fitness/sessions", {
            "title": "Sesion A",
            "session_date": "2026-01-01",
        }),
        "detail": [
            ("GET", "{id}", None),
            ("PUT", "{id}", {"title": "hackeada"}),
            ("DELETE", "{id}", None),
        ],
        "path": "/api/v1/fitness/sessions/{id}",
    },
    {
        "name": "meal",
        "create": ("POST", "/api/v1/nutrition/meals", {
            "meal_date": "2026-01-01",
            "name": "Comida A",
        }),
        "detail": [
            ("GET", "{id}", None),
            ("PUT", "{id}", {"name": "hackeada"}),
            ("DELETE", "{id}", None),
        ],
        "path": "/api/v1/nutrition/meals/{id}",
    },
    {
        "name": "event",
        "create": ("POST", "/api/v1/events", {
            "title": "Evento A",
            "start_datetime": "2026-01-01T10:00:00",
        }),
        "detail": [
            ("PUT", "{id}", {"title": "hackeado"}),
            ("DELETE", "{id}", None),
        ],
        "path": "/api/v1/events/{id}",
    },
    {
        "name": "goal",
        "create": ("POST", "/api/v1/goals", {"title": "Meta A"}),
        "detail": [
            ("PUT", "{id}", {"title": "hackeada"}),
            ("DELETE", "{id}", None),
        ],
        "path": "/api/v1/goals/{id}",
    },
    {
        "name": "investment",
        "create": ("POST", "/api/v1/finance/investments", {
            "asset_type": "stock",
            "name": "Inversion A",
            "currency": "ARS",
            "invested_amount": "1000",
        }),
        "detail": [
            ("GET", "{id}", None),
            ("PUT", "{id}", {"name": "hackeada"}),
            ("DELETE", "{id}", None),
        ],
        "path": "/api/v1/finance/investments/{id}",
    },
    {
        "name": "recurring transaction",
        "create": ("POST", "/api/v1/finance/recurring", {
            "type": "income",
            "name": "Sueldo A",
            "amount": "100",
            "frequency": "monthly",
            "day_of_month": 5,
            "start_date": "2099-01-01",
        }),
        "detail": [
            ("GET", "{id}", None),
            ("PUT", "{id}", {"name": "hackeada"}),
            ("DELETE", "{id}", None),
        ],
        "path": "/api/v1/finance/recurring/{id}",
    },
    {
        "name": "note",
        "create": ("POST", "/api/v1/notes", {"title": "Nota A", "content": "contenido"}),
        "detail": [
            ("PUT", "{id}", {"title": "hackeada"}),
            ("DELETE", "{id}", None),
        ],
        "path": "/api/v1/notes/{id}",
    },
]


@pytest.mark.parametrize("resource", RESOURCES, ids=[r["name"] for r in RESOURCES])
async def test_user_b_cannot_access_user_a_resource(resource, user_a, user_b):
    method, url, payload = resource["create"]
    create_resp = await user_a.request(method, url, json=payload)
    assert create_resp.status_code == 201, create_resp.text
    resource_id = create_resp.json()["id"]

    for method, path_template, body in resource["detail"]:
        url = resource["path"].replace("{id}", str(resource_id))
        resp = await user_b.request(method, url, json=body)
        assert resp.status_code == 404, (
            f"{resource['name']} {method} {url} devolvió {resp.status_code} "
            f"en vez de 404 para un recurso ajeno"
        )

    # Confirmar que el recurso sigue intacto/existente para su dueño real.
    own_check_method, own_path, own_body = resource["detail"][0]
    if own_check_method in ("GET",):
        own_resp = await user_a.request("GET", resource["path"].replace("{id}", str(resource_id)))
        assert own_resp.status_code == 200


async def test_user_b_cannot_see_user_a_tasks_in_list(user_a, user_b):
    await user_a.post("/api/v1/tasks", json={"title": "Tarea privada A"})
    resp = await user_b.get("/api/v1/tasks")
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()]
    assert "Tarea privada A" not in titles


async def test_user_b_cannot_see_user_a_notes_in_list(user_a, user_b):
    await user_a.post("/api/v1/notes", json={"title": "Nota privada A", "content": "secreto"})
    resp = await user_b.get("/api/v1/notes")
    assert resp.status_code == 200
    titles = [n["title"] for n in resp.json()]
    assert "Nota privada A" not in titles


async def test_user_b_cannot_read_user_a_habit_records(user_a, user_b):
    create_resp = await user_a.post("/api/v1/goals", json={
        "title": "Meta A",
        "goal_type": "metric",
        "target_value": 100,
    })
    assert create_resp.status_code == 201
    goal_id = create_resp.json()["id"]

    checkin_resp = await user_a.post(f"/api/v1/goals/{goal_id}/records", json={
        "record_date": "2026-01-01",
        "value": 10,
    })
    assert checkin_resp.status_code == 201

    # user_b nunca vio el goal_id (no le pertenece) -> 404 al intentar leer sus records.
    resp = await user_b.get(f"/api/v1/goals/{goal_id}/records", params={"year": 2026, "month": 1})
    assert resp.status_code == 404


async def test_bearer_only_client_still_respects_tenant_boundary(user_a, user_b):
    # Camino mobile: sin cookie, solo Bearer. Confirma que el aislamiento por
    # user_id se mantiene también en ese camino (no solo en el de cookie).
    create_resp = await user_a.post("/api/v1/tasks", json={"title": "Tarea A bearer"})
    task_id = create_resp.json()["id"]

    login_resp = await user_a.post("/auth/api/login", json={
        "email": "usera@test.com",
        "password": "testpass123",
    })
    token_a = login_resp.json()["access_token"]
    user_a.cookies.clear()

    resp = await user_a.get(
        "/api/v1/tasks", headers={"Authorization": f"Bearer {token_a}"}
    )
    assert resp.status_code == 200
    assert any(t["id"] == task_id for t in resp.json())

    resp = await user_b.patch(f"/api/v1/tasks/{task_id}", json={"title": "hackeada"})
    assert resp.status_code == 404


async def test_user_b_net_worth_no_cuenta_los_datos_de_user_a(user_a, user_b):
    await user_a.post("/api/v1/finance/transactions", json={
        "amount": "5000",
        "type": "income",
        "transaction_date": "2026-01-01",
        "account_type": "cash",
        "payment_method": "cash",
        "product_name": "Sueldo A",
    })
    await user_a.post("/api/v1/finance/investments", json={
        "asset_type": "stock",
        "name": "Inversion A",
        "currency": "ARS",
        "invested_amount": "7000",
    })
    resp = await user_b.get("/api/v1/finance/net-worth")
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["cash_balance_ars"]) == 0
    assert float(data["net_worth_ars"]) == 0
    assert data["investments"]["count_active"] == 0

    summary = (await user_b.get("/api/v1/finance/summary")).json()
    assert float(summary["investments_value_ars"]) == 0
    assert float(summary["net_worth_ars"]) == 0


# ── Datos de mercado: lo compartido es global, lo personal no se mezcla ─────


async def test_fuente_del_dolar_y_rendimiento_real_son_por_usuario(user_a, user_b):
    from datetime import datetime, timezone
    from decimal import Decimal

    from app.database import get_db
    from market_helpers import add_inflation, add_quote, months_back

    override = app.dependency_overrides[get_db]
    async for db in override():
        await add_quote(db, "USD", "blue", "1565", as_of=datetime.now(timezone.utc))
        await add_quote(db, "USD", "mep", "1563.9", as_of=datetime.now(timezone.utc))
        await add_inflation(db, {m: 2.0 for m in months_back(14)})

    await user_a.put("/api/v1/settings", json={"fx_usd_source": "blue"})
    assert (await user_b.get("/api/v1/settings")).json()["fx_usd_source"] == "mep"
    assert (await user_a.get("/api/v1/settings")).json()["fx_usd_source"] == "blue"

    for client in (user_a, user_b):
        await client.post("/api/v1/finance/investments", json={
            "asset_type": "fx", "name": "USD", "currency": "USD", "invested_amount": "100",
        })
    rates_a = (await user_a.get("/api/v1/finance/net-worth")).json()["rates"]
    rates_b = (await user_b.get("/api/v1/finance/net-worth")).json()["rates"]
    assert Decimal(rates_a["usd_ars"]) == Decimal("1565")
    assert Decimal(rates_b["usd_ars"]) == Decimal("1563.9")

    pf = await user_a.post("/api/v1/finance/investments", json={
        "asset_type": "stock", "name": "Con fecha", "currency": "ARS", "invested_amount": "1000",
        "current_value": "1100", "start_date": "2026-09-01",
    })
    assert pf.json()["real_return"] is not None
    summary_a = (await user_a.get("/api/v1/finance/investments/summary")).json()
    summary_b = (await user_b.get("/api/v1/finance/investments/summary")).json()
    assert summary_a["real_return_ars"]["included_count"] == 1
    assert summary_b["real_return_ars"] is None


async def test_user_b_no_toca_cripto_automatica_de_user_a(user_a, user_b):
    created = await user_a.post("/api/v1/finance/investments", json={
        "asset_type": "crypto", "name": "BTC", "ticker": "BTC", "currency": "USD",
        "quantity": "1", "invested_amount": "1000", "price_source": "coingecko",
    })
    assert created.status_code == 201, created.text
    url = f"/api/v1/finance/investments/{created.json()['id']}"
    assert (await user_b.put(url, json={"price_source": "manual", "current_value": "1"})).status_code == 404
    assert (await user_b.delete(url)).status_code == 404
    assert (await user_b.get(url)).status_code == 404
    assert (await user_a.get(url)).json()["price_source"] == "coingecko"
    assert (await user_b.get("/api/v1/finance/investments")).json() == []


async def test_user_b_no_toca_las_recurrentes_de_user_a(user_a, user_b):
    created = await user_a.post("/api/v1/finance/recurring", json={
        "type": "expense", "name": "Luz", "amount": "25000", "requires_confirmation": True,
        "frequency": "daily", "start_date": "2000-01-01", "generate_past": False,
    })
    # Inicio lejano en el pasado sin backfill: arranca hoy y deja un pendiente.
    assert created.status_code == 201, created.text
    rec_id = created.json()["id"]
    base = f"/api/v1/finance/recurring/{rec_id}"
    for method, suffix in (("POST", "/pause"), ("POST", "/resume")):
        assert (await user_b.request(method, base + suffix, json={})).status_code == 404

    occ_id = (await user_a.get("/api/v1/finance/recurring/occurrences")).json()[0]["id"]
    occ_url = f"/api/v1/finance/recurring/occurrences/{occ_id}"
    assert (await user_b.post(occ_url + "/confirm", json={"amount": "1"})).status_code == 404
    assert (await user_b.post(occ_url + "/skip", json={})).status_code == 404

    # Nada cambio para el dueño: sigue pendiente y sin transacciones.
    assert (await user_a.get("/api/v1/finance/recurring/occurrences")).json()[0]["status"] == "pending"
    assert (await user_a.get("/api/v1/finance/transactions")).json()["total"] == 0


async def test_las_listas_de_recurrentes_no_mezclan_usuarios(user_a, user_b):
    for client, name in ((user_a, "Pendiente de A"), (user_b, "Pendiente de B")):
        resp = await client.post("/api/v1/finance/recurring", json={
            "type": "expense", "name": name, "amount": "10", "requires_confirmation": True,
            "frequency": "daily", "start_date": "2000-01-01",
        })
        assert resp.status_code == 201, resp.text
        resp = await client.post("/api/v1/finance/recurring", json={
            "type": "income", "name": f"Sueldo {name}", "amount": "10",
            "frequency": "monthly", "day_of_month": 5, "start_date": "2000-01-01",
        })
        assert resp.status_code == 201, resp.text

    for client, own, other in ((user_a, "de A", "de B"), (user_b, "de B", "de A")):
        listed = (await client.get("/api/v1/finance/recurring")).json()
        assert {r["name"] for r in listed} == {f"Pendiente {own}", f"Sueldo Pendiente {own}"}
        pending = (await client.get("/api/v1/finance/recurring/occurrences")).json()
        assert [p["name"] for p in pending] == [f"Pendiente {own}"]
        upcoming = (await client.get("/api/v1/finance/recurring/upcoming")).json()
        assert all(other not in i["name"] for i in upcoming["items"])
        assert any(own in i["name"] for i in upcoming["items"])


async def test_user_b_no_renueva_ni_ve_renovaciones_de_user_a(user_a, user_b):
    from datetime import date, timedelta

    today = date.today()
    created = await user_a.post("/api/v1/finance/investments", json={
        "asset_type": "fixed_term", "name": "PF A", "currency": "ARS", "invested_amount": "1000",
        "interest_rate_tna": "30",
        "start_date": (today - timedelta(days=40)).isoformat(),
        "maturity_date": (today - timedelta(days=5)).isoformat(),
    })
    assert created.status_code == 201, created.text
    url = f"/api/v1/finance/investments/{created.json()['id']}"
    body = {"mode": "principal_and_interest", "interest_rate_tna": "28", "term_days": 30}
    assert (await user_b.post(url + "/renew", json=body)).status_code == 404
    assert (await user_b.get(url + "/renewals")).status_code == 404
    assert (await user_a.get(url)).json()["status"] == "active"


async def test_user_b_does_not_see_user_a_habit_reminders(user_a, user_b):
    created = await user_a.post("/api/v1/goals", json={
        "title": "Habito privado A",
        "goal_type": "binary",
        "reminder_time": "07:30",
    })
    assert created.status_code == 201
    goal_id = created.json()["id"]
    await user_a.put("/api/v1/habit-reminders/settings", json={"enabled": False, "time": "06:00"})

    # Lo de B es suyo: ni el habito, ni la hora, ni la configuracion de A.
    overview = (await user_b.get(
        "/api/v1/habit-reminders/today", params={"tz_offset_minutes": -180}
    )).json()
    assert overview["pending_count"] == 0 and overview["slots"] == []
    theirs = (await user_b.get("/api/v1/habit-reminders/settings")).json()
    assert theirs["enabled"] is True and theirs["time"] == "20:00"

    # Y B no puede editar el aviso del habito de A.
    resp = await user_b.put(f"/api/v1/goals/{goal_id}", json={"reminder_enabled": False})
    assert resp.status_code == 404
    mine = [g for g in (await user_a.get("/api/v1/goals")).json() if g["id"] == goal_id][0]
    assert mine["reminder_enabled"] is True and mine["reminder_time"] == "07:30"

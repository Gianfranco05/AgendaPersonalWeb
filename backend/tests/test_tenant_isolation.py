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

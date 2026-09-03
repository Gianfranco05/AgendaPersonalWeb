import pytest
import pytest_asyncio

from app.modules.modulos.service import ModulesService

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def owns_media(db_session, test_user):
    """La plantilla se compra antes de cada test: sin esto todo daria 402."""
    await ModulesService(db_session).grant(test_user.id, "media")


async def _crear_item(client, title="Interstellar", **extra):
    resp = await client.post("/api/v1/media/items", json={"title": title, **extra})
    assert resp.status_code == 201
    return resp.json()


# ── Gate de compra ───────────────────────────────────────────────────────────

async def test_media_endpoints_require_auth(client):
    assert (await client.get("/api/v1/media/items")).status_code == 401


async def test_media_endpoints_are_blocked_without_the_purchase(
    api_auth_client, db_session, test_user, monkeypatch
):
    """Confirma que este router esta enganchado a require_module("media") y
    no, por copy-paste, a otra plantilla.
    """
    from app.config import settings
    from app.modules.modulos.models import ModulePurchase
    from sqlalchemy import delete

    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")
    await db_session.execute(
        delete(ModulePurchase).where(
            ModulePurchase.user_id == test_user.id, ModulePurchase.module_key == "media"
        )
    )
    await db_session.commit()

    resp = await api_auth_client.get("/api/v1/media/items")
    assert resp.status_code == 402


# ── CRUD ─────────────────────────────────────────────────────────────────────

async def test_create_and_list_items(api_auth_client):
    await _crear_item(api_auth_client, "Interstellar", media_type="pelicula")
    await _crear_item(api_auth_client, "Breaking Bad", media_type="serie")

    items = (await api_auth_client.get("/api/v1/media/items")).json()
    assert {i["title"] for i in items} == {"Interstellar", "Breaking Bad"}
    assert all(i["status"] == "pendiente" for i in items)  # default


async def test_create_rejects_an_invalid_type(api_auth_client):
    resp = await api_auth_client.post(
        "/api/v1/media/items", json={"title": "X", "media_type": "documental"}
    )
    assert resp.status_code == 422


async def test_create_rejects_an_invalid_status(api_auth_client):
    resp = await api_auth_client.post(
        "/api/v1/media/items", json={"title": "X", "status": "inventado"}
    )
    assert resp.status_code == 422


async def test_rating_out_of_range_is_rejected(api_auth_client):
    resp = await api_auth_client.post("/api/v1/media/items", json={"title": "X", "rating": 9})
    assert resp.status_code == 422


async def test_update_item(api_auth_client):
    item = await _crear_item(api_auth_client)
    resp = await api_auth_client.patch(
        f"/api/v1/media/items/{item['id']}", json={"status": "visto", "rating": 5}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "visto"
    assert resp.json()["rating"] == 5


async def test_delete_item(api_auth_client):
    item = await _crear_item(api_auth_client)
    assert (await api_auth_client.delete(f"/api/v1/media/items/{item['id']}")).status_code == 204
    assert (await api_auth_client.get("/api/v1/media/items")).json() == []


async def test_filter_by_type_and_status(api_auth_client):
    pelicula = await _crear_item(api_auth_client, "Peli", media_type="pelicula", status="visto")
    await _crear_item(api_auth_client, "Serie", media_type="serie", status="viendo")

    resp = await api_auth_client.get("/api/v1/media/items", params={"media_type": "pelicula"})
    assert [i["id"] for i in resp.json()] == [pelicula["id"]]

    resp = await api_auth_client.get("/api/v1/media/items", params={"status": "visto"})
    assert [i["id"] for i in resp.json()] == [pelicula["id"]]


# ── Resumen ──────────────────────────────────────────────────────────────────

async def test_summary_averages_only_watched_items(api_auth_client):
    await _crear_item(api_auth_client, "Uno", status="visto", rating=5)
    await _crear_item(api_auth_client, "Dos", status="visto", rating=3)
    await _crear_item(api_auth_client, "Tres", status="pendiente", rating=1)  # no cuenta

    data = (await api_auth_client.get("/api/v1/media/summary")).json()
    assert data["total"] == 3
    assert data["vistos"] == 2
    assert data["average_rating"] == 4  # (5 + 3) / 2


async def test_summary_without_data(api_auth_client):
    data = (await api_auth_client.get("/api/v1/media/summary")).json()
    assert data["total"] == 0
    assert data["average_rating"] is None


# ── Aislamiento entre usuarios ───────────────────────────────────────────────

async def test_items_of_another_user_are_not_reachable(api_auth_client, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User
    from app.modules.peliculas.service import MediaService

    otro = User(
        email="otro_media@test.com",
        password_hash=hash_password("test123"),
        full_name="Otro",
        is_active=True,
    )
    db_session.add(otro)
    await db_session.commit()
    ajeno = await MediaService(db_session).create_item(otro.id, "Ajeno")

    assert (await api_auth_client.get("/api/v1/media/items")).json() == []
    assert (
        await api_auth_client.patch(f"/api/v1/media/items/{ajeno.id}", json={"title": "Hackeado"})
    ).status_code == 404
    assert (await api_auth_client.delete(f"/api/v1/media/items/{ajeno.id}")).status_code == 404

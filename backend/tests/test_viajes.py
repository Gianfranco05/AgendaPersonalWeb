from datetime import date, timedelta

import pytest
import pytest_asyncio

from app.modules.modulos.service import ModulesService

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def owns_travel(db_session, test_user):
    """La plantilla se compra antes de cada test: sin esto todo daria 402."""
    await ModulesService(db_session).grant(test_user.id, "travel")


async def _crear_viaje(client, destination="Bariloche", **extra):
    resp = await client.post("/api/v1/travel/trips", json={"destination": destination, **extra})
    assert resp.status_code == 201
    return resp.json()


# ── Gate de compra ───────────────────────────────────────────────────────────

async def test_travel_endpoints_require_auth(client):
    assert (await client.get("/api/v1/travel/trips")).status_code == 401


async def test_travel_endpoints_are_blocked_without_the_purchase(
    api_auth_client, db_session, test_user, monkeypatch
):
    from app.config import settings
    from app.modules.modulos.models import ModulePurchase
    from sqlalchemy import delete

    monkeypatch.setattr(settings, "BILLING_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")
    await db_session.execute(
        delete(ModulePurchase).where(
            ModulePurchase.user_id == test_user.id, ModulePurchase.module_key == "travel"
        )
    )
    await db_session.commit()

    resp = await api_auth_client.get("/api/v1/travel/trips")
    assert resp.status_code == 402


# ── Viajes ───────────────────────────────────────────────────────────────────

async def test_create_and_list_trips(api_auth_client):
    await _crear_viaje(api_auth_client, "Bariloche")
    await _crear_viaje(api_auth_client, "Roma")

    viajes = (await api_auth_client.get("/api/v1/travel/trips")).json()
    assert {t["destination"] for t in viajes} == {"Bariloche", "Roma"}
    assert all(t["status"] == "planeado" for t in viajes)  # default


async def test_create_rejects_an_invalid_status(api_auth_client):
    resp = await api_auth_client.post(
        "/api/v1/travel/trips", json={"destination": "X", "status": "inventado"}
    )
    assert resp.status_code == 422


async def test_update_trip(api_auth_client):
    viaje = await _crear_viaje(api_auth_client)
    resp = await api_auth_client.patch(
        f"/api/v1/travel/trips/{viaje['id']}", json={"status": "completado"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completado"


async def test_update_unknown_trip_is_404(api_auth_client):
    resp = await api_auth_client.patch("/api/v1/travel/trips/nope", json={"destination": "X"})
    assert resp.status_code == 404


async def test_trips_are_sorted_by_start_date_with_undated_last(api_auth_client):
    hoy = date.today()
    sin_fecha = await _crear_viaje(api_auth_client, "Sin fecha")
    lejano = await _crear_viaje(api_auth_client, "Lejano", start_date=(hoy + timedelta(days=30)).isoformat())
    cercano = await _crear_viaje(api_auth_client, "Cercano", start_date=(hoy + timedelta(days=5)).isoformat())

    viajes = (await api_auth_client.get("/api/v1/travel/trips")).json()
    assert [v["id"] for v in viajes] == [cercano["id"], lejano["id"], sin_fecha["id"]]


# ── Checklist de equipaje ────────────────────────────────────────────────────

async def test_add_and_list_packing_items(api_auth_client):
    viaje = await _crear_viaje(api_auth_client)
    resp = await api_auth_client.post(
        f"/api/v1/travel/trips/{viaje['id']}/items", json={"name": "Pasaporte"}
    )
    assert resp.status_code == 201
    assert resp.json()["packed"] is False  # default

    items = (await api_auth_client.get(f"/api/v1/travel/trips/{viaje['id']}/items")).json()
    assert [i["name"] for i in items] == ["Pasaporte"]


async def test_cannot_add_items_to_another_users_trip(api_auth_client, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User
    from app.modules.viajes.service import TravelService

    otro = User(
        email="otro_viaje@test.com",
        password_hash=hash_password("test123"),
        full_name="Otro",
        is_active=True,
    )
    db_session.add(otro)
    await db_session.commit()
    viaje_ajeno = await TravelService(db_session).create_trip(otro.id, "Ajeno")

    resp = await api_auth_client.post(
        f"/api/v1/travel/trips/{viaje_ajeno.id}/items", json={"name": "Colado"}
    )
    assert resp.status_code == 404


async def test_toggle_packed_and_delete_item(api_auth_client):
    viaje = await _crear_viaje(api_auth_client)
    item = (
        await api_auth_client.post(
            f"/api/v1/travel/trips/{viaje['id']}/items", json={"name": "Cargador"}
        )
    ).json()

    resp = await api_auth_client.patch(f"/api/v1/travel/items/{item['id']}", json={"packed": True})
    assert resp.status_code == 200
    assert resp.json()["packed"] is True

    assert (
        await api_auth_client.delete(f"/api/v1/travel/items/{item['id']}")
    ).status_code == 204
    assert (await api_auth_client.get(f"/api/v1/travel/trips/{viaje['id']}/items")).json() == []


async def test_deleting_a_trip_also_deletes_its_packing_list(api_auth_client, db_session):
    viaje = await _crear_viaje(api_auth_client)
    await api_auth_client.post(f"/api/v1/travel/trips/{viaje['id']}/items", json={"name": "X"})

    assert (await api_auth_client.delete(f"/api/v1/travel/trips/{viaje['id']}")).status_code == 204

    from sqlalchemy import select
    from app.modules.viajes.models import PackingItem

    restantes = (await db_session.execute(select(PackingItem))).scalars().all()
    assert list(restantes) == []


# ── Resumen ──────────────────────────────────────────────────────────────────

async def test_summary_counts_and_next_trip(api_auth_client):
    hoy = date.today()
    await _crear_viaje(api_auth_client, "Pasado", status="completado")
    await _crear_viaje(
        api_auth_client, "Próximo", start_date=(hoy + timedelta(days=10)).isoformat()
    )

    data = (await api_auth_client.get("/api/v1/travel/summary")).json()
    assert data["total"] == 2
    assert data["completados"] == 1
    assert data["planeados"] == 1
    assert data["next_trip"]["destination"] == "Próximo"


async def test_summary_without_data(api_auth_client):
    data = (await api_auth_client.get("/api/v1/travel/summary")).json()
    assert data["total"] == 0
    assert data["next_trip"] is None

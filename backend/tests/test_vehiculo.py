from datetime import date

import pytest
import pytest_asyncio

from app.modules.modulos.service import ModulesService

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def owns_vehicle(db_session, test_user):
    """La plantilla se compra antes de cada test: sin esto todo daria 402."""
    await ModulesService(db_session).grant(test_user.id, "vehicle")


async def _crear_vehiculo(client, name="Mi Auto", **extra):
    resp = await client.post("/api/v1/vehicle/vehicles", json={"name": name, **extra})
    assert resp.status_code == 201
    return resp.json()


# ── Gate de compra ───────────────────────────────────────────────────────────

async def test_vehicle_endpoints_require_auth(client):
    assert (await client.get("/api/v1/vehicle/vehicles")).status_code == 401


async def test_vehicle_endpoints_are_blocked_without_the_purchase(
    api_auth_client, db_session, test_user, monkeypatch
):
    from app.config import settings
    from app.modules.modulos.models import ModulePurchase
    from sqlalchemy import delete

    monkeypatch.setattr(settings, "BILLING_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")
    await db_session.execute(
        delete(ModulePurchase).where(
            ModulePurchase.user_id == test_user.id, ModulePurchase.module_key == "vehicle"
        )
    )
    await db_session.commit()

    resp = await api_auth_client.get("/api/v1/vehicle/vehicles")
    assert resp.status_code == 402


# ── Vehiculos ────────────────────────────────────────────────────────────────

async def test_create_and_list_vehicles(api_auth_client):
    await _crear_vehiculo(api_auth_client, "Auto", brand="Toyota")
    await _crear_vehiculo(api_auth_client, "Moto", brand="Honda")

    vehiculos = (await api_auth_client.get("/api/v1/vehicle/vehicles")).json()
    assert {v["name"] for v in vehiculos} == {"Auto", "Moto"}


async def test_update_and_delete_vehicle(api_auth_client):
    vehiculo = await _crear_vehiculo(api_auth_client)
    resp = await api_auth_client.patch(
        f"/api/v1/vehicle/vehicles/{vehiculo['id']}", json={"plate": "AB123CD"}
    )
    assert resp.status_code == 200
    assert resp.json()["plate"] == "AB123CD"

    assert (
        await api_auth_client.delete(f"/api/v1/vehicle/vehicles/{vehiculo['id']}")
    ).status_code == 204
    assert (await api_auth_client.get("/api/v1/vehicle/vehicles")).json() == []


async def test_update_unknown_vehicle_is_404(api_auth_client):
    resp = await api_auth_client.patch("/api/v1/vehicle/vehicles/nope", json={"name": "X"})
    assert resp.status_code == 404


# ── Historial ────────────────────────────────────────────────────────────────

async def test_create_record_requires_a_valid_type(api_auth_client):
    vehiculo = await _crear_vehiculo(api_auth_client)
    resp = await api_auth_client.post(
        "/api/v1/vehicle/records",
        json={
            "vehicle_id": vehiculo["id"],
            "record_type": "inventado",
            "record_date": date.today().isoformat(),
        },
    )
    assert resp.status_code == 422


async def test_create_record_for_an_unknown_vehicle_is_404(api_auth_client):
    resp = await api_auth_client.post(
        "/api/v1/vehicle/records",
        json={
            "vehicle_id": "no-existe",
            "record_type": "combustible",
            "record_date": date.today().isoformat(),
        },
    )
    assert resp.status_code == 404


async def test_create_and_list_records(api_auth_client):
    vehiculo = await _crear_vehiculo(api_auth_client)
    resp = await api_auth_client.post(
        "/api/v1/vehicle/records",
        json={
            "vehicle_id": vehiculo["id"],
            "record_type": "combustible",
            "record_date": date.today().isoformat(),
            "cost": 15000,
            "odometer_km": 32000,
        },
    )
    assert resp.status_code == 201

    records = (await api_auth_client.get("/api/v1/vehicle/records")).json()
    assert len(records) == 1
    assert records[0]["cost"] == 15000


async def test_filter_records_by_vehicle_and_type(api_auth_client):
    auto = await _crear_vehiculo(api_auth_client, "Auto")
    moto = await _crear_vehiculo(api_auth_client, "Moto")

    await api_auth_client.post(
        "/api/v1/vehicle/records",
        json={"vehicle_id": auto["id"], "record_type": "itv", "record_date": date.today().isoformat()},
    )
    await api_auth_client.post(
        "/api/v1/vehicle/records",
        json={
            "vehicle_id": moto["id"],
            "record_type": "combustible",
            "record_date": date.today().isoformat(),
        },
    )

    solo_auto = (
        await api_auth_client.get("/api/v1/vehicle/records", params={"vehicle_id": auto["id"]})
    ).json()
    assert len(solo_auto) == 1
    assert solo_auto[0]["record_type"] == "itv"

    solo_combustible = (
        await api_auth_client.get("/api/v1/vehicle/records", params={"record_type": "combustible"})
    ).json()
    assert len(solo_combustible) == 1
    assert solo_combustible[0]["vehicle_id"] == moto["id"]


async def test_deleting_a_vehicle_also_deletes_its_records(api_auth_client, db_session):
    vehiculo = await _crear_vehiculo(api_auth_client)
    await api_auth_client.post(
        "/api/v1/vehicle/records",
        json={
            "vehicle_id": vehiculo["id"],
            "record_type": "gasto",
            "record_date": date.today().isoformat(),
        },
    )

    assert (
        await api_auth_client.delete(f"/api/v1/vehicle/vehicles/{vehiculo['id']}")
    ).status_code == 204

    from sqlalchemy import select
    from app.modules.vehiculo.models import MaintenanceRecord

    restantes = (await db_session.execute(select(MaintenanceRecord))).scalars().all()
    assert list(restantes) == []


# ── Resumen ──────────────────────────────────────────────────────────────────

async def test_summary_sums_costs_and_finds_last_record(api_auth_client):
    vehiculo = await _crear_vehiculo(api_auth_client)
    await api_auth_client.post(
        "/api/v1/vehicle/records",
        json={
            "vehicle_id": vehiculo["id"],
            "record_type": "combustible",
            "record_date": "2026-01-01",
            "cost": 100,
        },
    )
    await api_auth_client.post(
        "/api/v1/vehicle/records",
        json={
            "vehicle_id": vehiculo["id"],
            "record_type": "itv",
            "record_date": "2026-06-01",
            "cost": 50,
        },
    )

    data = (await api_auth_client.get("/api/v1/vehicle/summary")).json()
    assert data["vehicles_total"] == 1
    assert data["records_total"] == 2
    assert data["total_spent"] == 150
    assert data["last_record"]["record_type"] == "itv"  # el mas reciente


async def test_summary_without_data(api_auth_client):
    data = (await api_auth_client.get("/api/v1/vehicle/summary")).json()
    assert data["vehicles_total"] == 0
    assert data["total_spent"] == 0.0
    assert data["last_record"] is None


# ── Aislamiento entre usuarios ───────────────────────────────────────────────

async def test_vehicles_of_another_user_are_not_reachable(api_auth_client, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User
    from app.modules.vehiculo.service import VehicleService

    otro = User(
        email="otro_vehiculo@test.com",
        password_hash=hash_password("test123"),
        full_name="Otro",
        is_active=True,
    )
    db_session.add(otro)
    await db_session.commit()
    ajeno = await VehicleService(db_session).create_vehicle(otro.id, "Ajeno")

    assert (await api_auth_client.get("/api/v1/vehicle/vehicles")).json() == []
    assert (
        await api_auth_client.patch(f"/api/v1/vehicle/vehicles/{ajeno.id}", json={"name": "Hackeado"})
    ).status_code == 404

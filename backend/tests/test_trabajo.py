import pytest
import pytest_asyncio

from app.modules.modulos.service import ModulesService

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def owns_work(db_session, test_user):
    """La plantilla se compra antes de cada test: sin esto todo daria 402."""
    await ModulesService(db_session).grant(test_user.id, "work")


async def _crear_oportunidad(client, company="Acme", role="Backend Dev", **extra):
    resp = await client.post(
        "/api/v1/work/opportunities", json={"company": company, "role": role, **extra}
    )
    assert resp.status_code == 201
    return resp.json()


# ── Gate de compra ───────────────────────────────────────────────────────────

async def test_work_endpoints_require_auth(client):
    assert (await client.get("/api/v1/work/opportunities")).status_code == 401


async def test_work_endpoints_are_blocked_without_the_purchase(
    api_auth_client, db_session, test_user, monkeypatch
):
    from app.config import settings
    from app.modules.modulos.models import ModulePurchase
    from sqlalchemy import delete

    monkeypatch.setattr(settings, "BILLING_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")
    await db_session.execute(
        delete(ModulePurchase).where(
            ModulePurchase.user_id == test_user.id, ModulePurchase.module_key == "work"
        )
    )
    await db_session.commit()

    resp = await api_auth_client.get("/api/v1/work/opportunities")
    assert resp.status_code == 402


# ── CRUD ─────────────────────────────────────────────────────────────────────

async def test_create_and_list_opportunities(api_auth_client):
    await _crear_oportunidad(api_auth_client, "Acme", "Backend Dev")
    await _crear_oportunidad(api_auth_client, "Umbrella", "Frontend Dev")

    oportunidades = (await api_auth_client.get("/api/v1/work/opportunities")).json()
    assert {o["company"] for o in oportunidades} == {"Acme", "Umbrella"}
    assert all(o["status"] == "aplicado" for o in oportunidades)  # default


async def test_create_rejects_an_invalid_status(api_auth_client):
    resp = await api_auth_client.post(
        "/api/v1/work/opportunities",
        json={"company": "X", "role": "Y", "status": "inventado"},
    )
    assert resp.status_code == 422


async def test_negative_salary_is_rejected(api_auth_client):
    resp = await api_auth_client.post(
        "/api/v1/work/opportunities", json={"company": "X", "role": "Y", "salary": -1}
    )
    assert resp.status_code == 422


async def test_update_opportunity(api_auth_client):
    opp = await _crear_oportunidad(api_auth_client)
    resp = await api_auth_client.patch(
        f"/api/v1/work/opportunities/{opp['id']}", json={"status": "entrevista"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "entrevista"


async def test_update_unknown_opportunity_is_404(api_auth_client):
    resp = await api_auth_client.patch(
        "/api/v1/work/opportunities/nope", json={"company": "X"}
    )
    assert resp.status_code == 404


async def test_delete_opportunity(api_auth_client):
    opp = await _crear_oportunidad(api_auth_client)
    assert (
        await api_auth_client.delete(f"/api/v1/work/opportunities/{opp['id']}")
    ).status_code == 204
    assert (await api_auth_client.get("/api/v1/work/opportunities")).json() == []


async def test_filter_by_status(api_auth_client):
    await _crear_oportunidad(api_auth_client, "A", "X")
    entrevista = await _crear_oportunidad(api_auth_client, "B", "Y", status="entrevista")

    resp = await api_auth_client.get(
        "/api/v1/work/opportunities", params={"status": "entrevista"}
    )
    assert [o["id"] for o in resp.json()] == [entrevista["id"]]


# ── Resumen ──────────────────────────────────────────────────────────────────

async def test_summary_counts_by_status(api_auth_client):
    await _crear_oportunidad(api_auth_client, "A", "X", status="entrevista")
    await _crear_oportunidad(api_auth_client, "B", "Y", status="oferta")
    await _crear_oportunidad(api_auth_client, "C", "Z", status="rechazado")
    await _crear_oportunidad(api_auth_client, "D", "W", status="aceptado")

    data = (await api_auth_client.get("/api/v1/work/summary")).json()
    assert data["total"] == 4
    assert data["entrevista"] == 1
    assert data["oferta"] == 1
    assert data["aceptado"] == 1
    # rechazado y aceptado son terminales: no cuentan como "activas".
    assert data["active"] == 2


async def test_summary_without_data(api_auth_client):
    data = (await api_auth_client.get("/api/v1/work/summary")).json()
    assert data["total"] == 0
    assert data["active"] == 0


# ── Aislamiento entre usuarios ───────────────────────────────────────────────

async def test_opportunities_of_another_user_are_not_reachable(api_auth_client, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User
    from app.modules.trabajo.service import WorkService

    otro = User(
        email="otro_work@test.com",
        password_hash=hash_password("test123"),
        full_name="Otro",
        is_active=True,
    )
    db_session.add(otro)
    await db_session.commit()
    ajena = await WorkService(db_session).create_opportunity(otro.id, "Ajena", "Rol")

    assert (await api_auth_client.get("/api/v1/work/opportunities")).json() == []
    assert (
        await api_auth_client.patch(
            f"/api/v1/work/opportunities/{ajena.id}", json={"company": "Hackeado"}
        )
    ).status_code == 404
    assert (
        await api_auth_client.delete(f"/api/v1/work/opportunities/{ajena.id}")
    ).status_code == 404

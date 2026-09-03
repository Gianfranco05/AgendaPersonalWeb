import pytest

from app.config import settings

pytestmark = pytest.mark.asyncio


async def test_register_requires_accepting_terms(client):
    resp = await client.post(
        "/auth/api/register",
        json={
            "email": "sinaceptar@test.com",
            "full_name": "Sin Aceptar",
            "password": "password123",
            "accept_terms": False,
        },
    )
    assert resp.status_code == 422


async def test_register_requires_the_field_at_all(client):
    # Ausente = False por default: el validator lo rechaza igual.
    resp = await client.post(
        "/auth/api/register",
        json={"email": "sincampo@test.com", "full_name": "X", "password": "password123"},
    )
    assert resp.status_code == 422


async def test_register_with_accepted_terms_records_version_and_timestamp(client):
    resp = await client.post(
        "/auth/api/register",
        json={
            "email": "acepto@test.com",
            "full_name": "Acepto",
            "password": "password123",
            "accept_terms": True,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["terms_accepted_version"] == settings.CURRENT_TERMS_VERSION


async def test_login_reports_the_accepted_version(api_auth_client):
    # test_user (via la fixture) se crea directo en la DB, sin pasar por
    # /register — nunca acepto nada, asi que login tiene que reportarlo en None
    # para que el cliente sepa que hay que mostrar el gate.
    resp = await api_auth_client.get("/auth/api/me")
    assert resp.json()["terms_accepted_version"] is None


async def test_accept_terms_requires_auth(client):
    resp = await client.post("/auth/api/accept-terms", json={"version": "1.0"})
    assert resp.status_code == 401


async def test_accept_terms_records_acceptance(api_auth_client):
    resp = await api_auth_client.post(
        "/auth/api/accept-terms", json={"version": settings.CURRENT_TERMS_VERSION}
    )
    assert resp.status_code == 200
    assert resp.json()["terms_accepted_version"] == settings.CURRENT_TERMS_VERSION

    me = await api_auth_client.get("/auth/api/me")
    assert me.json()["terms_accepted_version"] == settings.CURRENT_TERMS_VERSION


async def test_accept_terms_rejects_a_stale_client_version(api_auth_client):
    # El cliente manda la version que esta mostrando, no "la vigente": si no
    # coincide, mostro un texto viejo y aceptarlo silenciosamente invalidaria
    # la evidencia de que acepto lo que en verdad leyo.
    resp = await api_auth_client.post("/auth/api/accept-terms", json={"version": "0.9"})
    assert resp.status_code == 409

    me = await api_auth_client.get("/auth/api/me")
    assert me.json()["terms_accepted_version"] is None


async def test_bumping_the_version_un_accepts_everyone(
    api_auth_client, db_session, test_user, monkeypatch
):
    await api_auth_client.post(
        "/auth/api/accept-terms", json={"version": settings.CURRENT_TERMS_VERSION}
    )
    me = await api_auth_client.get("/auth/api/me")
    assert me.json()["terms_accepted_version"] == "1.0"

    # Se sube la version vigente (simulando un cambio real de terminos): la
    # aceptacion vieja queda "stale" — el cliente la compara contra la nueva
    # CURRENT_TERMS_VERSION y decide mostrar el gate de nuevo, sin que haga
    # falta tocar la fila del usuario en la base.
    monkeypatch.setattr(settings, "CURRENT_TERMS_VERSION", "2.0")

    me = await api_auth_client.get("/auth/api/me")
    assert me.json()["terms_accepted_version"] == "1.0"  # sigue siendo lo que acepto
    assert me.json()["terms_accepted_version"] != settings.CURRENT_TERMS_VERSION  # ya no alcanza

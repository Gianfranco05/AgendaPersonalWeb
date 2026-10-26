from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.config import settings
from app.core.security import hash_password
from app.modules.auth.models import User

pytestmark = pytest.mark.asyncio


async def test_register_requires_accepting_terms(client):
    resp = await client.post(
        "/auth/api/register",
        json={
            "email": "sinaceptar@test.com",
            "full_name": "Sin Aceptar",
            "password": "password123",
            "accept_terms": False,
            "confirm_age": True,
        },
    )
    assert resp.status_code == 422


async def test_register_requires_the_field_at_all(client):
    # Ausente = False por default: el validator lo rechaza igual.
    resp = await client.post(
        "/auth/api/register",
        json={
            "email": "sincampo@test.com",
            "full_name": "X",
            "password": "password123",
            "confirm_age": True,
        },
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
            "confirm_age": True,
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
    resp = await client.post(
        "/auth/api/accept-terms",
        json={"version": settings.CURRENT_TERMS_VERSION, "confirm_age": True},
    )
    assert resp.status_code == 401


async def test_accept_terms_records_acceptance(api_auth_client):
    resp = await api_auth_client.post(
        "/auth/api/accept-terms",
        json={"version": settings.CURRENT_TERMS_VERSION, "confirm_age": True},
    )
    assert resp.status_code == 200
    assert resp.json()["terms_accepted_version"] == settings.CURRENT_TERMS_VERSION

    me = await api_auth_client.get("/auth/api/me")
    assert me.json()["terms_accepted_version"] == settings.CURRENT_TERMS_VERSION


async def test_accept_terms_rejects_a_stale_client_version(api_auth_client):
    # El cliente manda la version que esta mostrando, no "la vigente": si no
    # coincide, mostro un texto viejo y aceptarlo silenciosamente invalidaria
    # la evidencia de que acepto lo que en verdad leyo.
    resp = await api_auth_client.post(
        "/auth/api/accept-terms", json={"version": "0.9", "confirm_age": True}
    )
    assert resp.status_code == 409

    me = await api_auth_client.get("/auth/api/me")
    assert me.json()["terms_accepted_version"] is None


async def test_bumping_the_version_un_accepts_everyone(
    api_auth_client, db_session, test_user, monkeypatch
):
    await api_auth_client.post(
        "/auth/api/accept-terms",
        json={"version": settings.CURRENT_TERMS_VERSION, "confirm_age": True},
    )
    me = await api_auth_client.get("/auth/api/me")
    accepted = settings.CURRENT_TERMS_VERSION
    assert me.json()["terms_accepted_version"] == accepted

    # Se sube la version vigente (simulando un cambio real de terminos): la
    # aceptacion vieja queda "stale" — el cliente la compara contra la nueva
    # CURRENT_TERMS_VERSION y decide mostrar el gate de nuevo, sin que haga
    # falta tocar la fila del usuario en la base.
    monkeypatch.setattr(settings, "CURRENT_TERMS_VERSION", "2.0")

    me = await api_auth_client.get("/auth/api/me")
    assert me.json()["terms_accepted_version"] == accepted  # sigue siendo lo que acepto
    assert me.json()["terms_accepted_version"] != settings.CURRENT_TERMS_VERSION  # ya no alcanza


# ── Declaracion de edad minima (16+) ────────────────────────────────────────


def _register_payload(email: str, **overrides) -> dict:
    payload = {
        "email": email,
        "full_name": "Edad",
        "password": "password123",
        "accept_terms": True,
        "confirm_age": True,
    }
    payload.update(overrides)
    return payload


async def _user_by_email(db_session, email: str):
    result = await db_session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def test_current_terms_version_is_1_1():
    # 1.1 agrega la declaracion de edad a la seccion 2 de los Terminos.
    assert settings.CURRENT_TERMS_VERSION == "1.1"


async def test_register_rejects_confirm_age_false(client, db_session):
    resp = await client.post(
        "/auth/api/register", json=_register_payload("menor@test.com", confirm_age=False)
    )
    assert resp.status_code == 422
    assert "16 años" in resp.text
    assert await _user_by_email(db_session, "menor@test.com") is None


async def test_register_rejects_missing_confirm_age(client, db_session):
    payload = _register_payload("sinedad@test.com")
    del payload["confirm_age"]
    resp = await client.post("/auth/api/register", json=payload)
    assert resp.status_code == 422
    assert await _user_by_email(db_session, "sinedad@test.com") is None


async def test_register_without_age_does_not_send_the_verification_email(
    client, monkeypatch
):
    enviados = []

    async def fake_send(email, token):
        enviados.append(email)

    monkeypatch.setattr("app.modules.auth.api_routes.send_verification_email", fake_send)
    resp = await client.post(
        "/auth/api/register", json=_register_payload("sinmail@test.com", confirm_age=False)
    )
    assert resp.status_code == 422
    assert enviados == []


async def test_register_with_confirm_age_stores_the_declaration(client, db_session):
    resp = await client.post("/auth/api/register", json=_register_payload("edad@test.com"))
    assert resp.status_code == 201
    data = resp.json()
    assert data["age_confirmed"] is True
    assert data["terms_accepted_version"] == "1.1"

    user = await _user_by_email(db_session, "edad@test.com")
    assert user.age_confirmed_at is not None
    assert user.terms_accepted_at is not None


async def test_register_login_and_me_expose_age_confirmed(client):
    await client.post("/auth/api/register", json=_register_payload("expone@test.com"))
    login = await client.post(
        "/auth/api/login", json={"email": "expone@test.com", "password": "password123"}
    )
    assert login.json()["age_confirmed"] is True
    me = await client.get("/auth/api/me")
    assert me.json()["age_confirmed"] is True
    assert "age_confirmed_at" not in me.json()


async def test_existing_user_has_age_confirmed_false(api_auth_client):
    # test_user se crea directo en la DB (como una cuenta anterior a este campo).
    me = await api_auth_client.get("/auth/api/me")
    assert me.json()["age_confirmed"] is False
    login = await api_auth_client.post(
        "/auth/api/login", json={"email": "test@test.com", "password": "test123"}
    )
    assert login.json()["age_confirmed"] is False


async def test_user_who_accepted_1_0_is_not_on_the_current_version(client, db_session):
    db_session.add(
        User(
            email="viejo@test.com",
            password_hash=hash_password("password123"),
            full_name="Viejo",
            is_verified=True,
            terms_accepted_version="1.0",
            terms_accepted_at=datetime.now(timezone.utc),
        )
    )
    await db_session.commit()
    login = await client.post(
        "/auth/api/login", json={"email": "viejo@test.com", "password": "password123"}
    )
    data = login.json()
    assert data["terms_accepted_version"] == "1.0"
    assert data["current_terms_version"] == "1.1"
    assert data["age_confirmed"] is False

    # Acepta 1.1 declarando la edad: queda al dia.
    resp = await client.post(
        "/auth/api/accept-terms", json={"version": "1.1", "confirm_age": True}
    )
    assert resp.status_code == 200
    assert resp.json()["terms_accepted_version"] == "1.1"
    assert resp.json()["age_confirmed"] is True


@pytest.mark.parametrize("body_extra", [{"confirm_age": False}, {}])
async def test_accept_terms_requires_confirm_age(
    api_auth_client, db_session, test_user, body_extra
):
    resp = await api_auth_client.post(
        "/auth/api/accept-terms",
        json={"version": settings.CURRENT_TERMS_VERSION, **body_extra},
    )
    assert resp.status_code == 422

    await db_session.refresh(test_user)
    assert test_user.terms_accepted_version is None
    assert test_user.terms_accepted_at is None
    assert test_user.age_confirmed_at is None
    me = await api_auth_client.get("/auth/api/me")
    assert me.json()["terms_accepted_version"] is None
    assert me.json()["age_confirmed"] is False


async def test_accept_terms_with_confirm_age_sets_age_confirmed(
    api_auth_client, db_session, test_user
):
    resp = await api_auth_client.post(
        "/auth/api/accept-terms",
        json={"version": settings.CURRENT_TERMS_VERSION, "confirm_age": True},
    )
    assert resp.status_code == 200
    assert resp.json()["age_confirmed"] is True
    await db_session.refresh(test_user)
    assert test_user.age_confirmed_at is not None


async def test_accept_terms_stale_version_does_not_set_age(
    api_auth_client, db_session, test_user
):
    resp = await api_auth_client.post(
        "/auth/api/accept-terms", json={"version": "0.9", "confirm_age": True}
    )
    assert resp.status_code == 409
    await db_session.refresh(test_user)
    assert test_user.age_confirmed_at is None


async def test_second_acceptance_keeps_the_first_age_confirmation(
    api_auth_client, db_session, test_user, monkeypatch
):
    await api_auth_client.post(
        "/auth/api/accept-terms",
        json={"version": settings.CURRENT_TERMS_VERSION, "confirm_age": True},
    )
    await db_session.refresh(test_user)
    primera_edad = test_user.age_confirmed_at
    primera_aceptacion = test_user.terms_accepted_at
    assert primera_edad is not None

    monkeypatch.setattr(settings, "CURRENT_TERMS_VERSION", "2.0")
    resp = await api_auth_client.post(
        "/auth/api/accept-terms", json={"version": "2.0", "confirm_age": True}
    )
    assert resp.status_code == 200

    await db_session.refresh(test_user)
    assert test_user.terms_accepted_version == "2.0"
    assert test_user.age_confirmed_at == primera_edad
    assert test_user.terms_accepted_at >= primera_aceptacion

"""Login con Google: el intercambio con Google se mockea (no se llama a la
API real). Lo que se prueba es la logica propia: el guard de open-redirect,
la firma/verificacion del state, y el alta-o-login por email."""

from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import unquote

import pytest
from sqlalchemy import select

from app.config import settings
from app.modules.auth.models import User


@pytest.fixture(autouse=True)
def _google_configured(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "fake-client-id")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "fake-client-secret")


@pytest.mark.asyncio
async def test_login_start_without_config_returns_503(client, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")
    response = await client.get(
        "/auth/api/google/login", params={"app_redirect": "exp://192.168.1.34:8081"}
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_login_start_rejects_disallowed_redirect(client):
    response = await client.get(
        "/auth/api/google/login",
        params={"app_redirect": "https://evil.example.com/steal"},
        follow_redirects=False,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_start_redirects_to_google_with_signed_state(client):
    response = await client.get(
        "/auth/api/google/login",
        params={"app_redirect": "exp://192.168.1.34:8081/--/redirect"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/auth")
    assert "state=" in location


@pytest.mark.asyncio
async def test_callback_without_state_is_rejected(client):
    response = await client.get(
        "/auth/api/google/callback", params={"code": "fake-code"}, follow_redirects=False
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_callback_with_tampered_state_is_rejected(client):
    start = await client.get(
        "/auth/api/google/login",
        params={"app_redirect": "exp://192.168.1.34:8081"},
        follow_redirects=False,
    )
    state = unquote(start.headers["location"].split("state=")[1].split("&")[0])
    tampered = state[:-4] + "0000"

    response = await client.get(
        "/auth/api/google/callback",
        params={"code": "fake-code", "state": tampered},
        follow_redirects=False,
    )
    assert response.status_code == 400


def _mock_google_exchange(email: str, name: str = "Nombre De Google"):
    """Parchea el intercambio de codigo y la verificacion del id_token para
    que devuelvan una identidad fija, sin llamar a Google."""
    mock_flow = MagicMock()
    mock_flow.fetch_token = MagicMock()
    mock_flow.credentials = MagicMock(id_token="fake-id-token")

    return patch.multiple(
        "app.modules.auth.api_routes",
        _build_google_login_flow=MagicMock(return_value=mock_flow),
    ), patch(
        "google.oauth2.id_token.verify_oauth2_token",
        return_value={"email": email, "name": name},
    )


@pytest.mark.asyncio
async def test_callback_creates_new_user_and_redirect_carries_working_tokens(client, db_session):
    email = "nueva-cuenta-google@example.com"
    start = await client.get(
        "/auth/api/google/login",
        params={"app_redirect": "exp://192.168.1.34:8081/--/redirect"},
        follow_redirects=False,
    )
    state = unquote(start.headers["location"].split("state=")[1].split("&")[0])

    patch_flow, patch_verify = _mock_google_exchange(email)
    with patch_flow, patch_verify:
        response = await client.get(
            "/auth/api/google/callback",
            params={"code": "fake-code", "state": state},
            follow_redirects=False,
        )

    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("exp://192.168.1.34:8081/--/redirect?")
    assert "access_token=" in location
    assert "refresh_token=" in location

    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.is_verified is True  # Google ya verifico el email

    # El access_token que viaja en el redirect tiene que servir de verdad.
    access_token = location.split("access_token=")[1].split("&")[0]
    me = await client.get("/auth/api/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email


@pytest.mark.asyncio
async def test_callback_logs_into_existing_account_by_email_without_duplicating(
    client, db_session, test_user
):
    start = await client.get(
        "/auth/api/google/login",
        params={"app_redirect": "exp://192.168.1.34:8081"},
        follow_redirects=False,
    )
    state = unquote(start.headers["location"].split("state=")[1].split("&")[0])

    patch_flow, patch_verify = _mock_google_exchange(test_user.email)
    with patch_flow, patch_verify:
        response = await client.get(
            "/auth/api/google/callback",
            params={"code": "fake-code", "state": state},
            follow_redirects=False,
        )

    assert response.status_code == 303
    result = await db_session.execute(select(User).where(User.email == test_user.email))
    users = result.scalars().all()
    assert len(users) == 1
    assert users[0].id == test_user.id


async def _callback(client, patch_flow, patch_verify):
    start = await client.get(
        "/auth/api/google/login",
        params={"app_redirect": "exp://192.168.1.34:8081"},
        follow_redirects=False,
    )
    state = unquote(start.headers["location"].split("state=")[1].split("&")[0])
    with patch_flow, patch_verify:
        return await client.get(
            "/auth/api/google/callback",
            params={"code": "fake-code", "state": state},
            follow_redirects=False,
        )


@pytest.mark.asyncio
async def test_callback_cuenta_no_verificada_pierde_la_password_y_las_sesiones(
    client, db_session
):
    """Pre-hijacking: alguien se registra con el email de otra persona (nada lo
    impide) y conoce la password. Cuando la duenia real entra con Google, la
    cuenta tiene que dejar de ser accesible para quien la registro."""
    from app.core.security import hash_password
    from app.modules.auth.models import RefreshToken

    victima = User(
        email="victima@example.com",
        password_hash=hash_password("passatacante"),
        full_name="Atacante",
        is_verified=False,
    )
    db_session.add(victima)
    await db_session.commit()
    login = await client.post(
        "/auth/api/login", json={"email": "victima@example.com", "password": "passatacante"}
    )
    assert login.status_code == 200
    atacante_refresh = login.json()["refresh_token"]

    patch_flow, patch_verify = _mock_google_exchange("victima@example.com")
    response = await _callback(client, patch_flow, patch_verify)
    assert response.status_code == 303
    assert "access_token=" in response.headers["location"]

    # La password del atacante ya no sirve, ni su refresh token.
    relogin = await client.post(
        "/auth/api/login", json={"email": "victima@example.com", "password": "passatacante"}
    )
    assert relogin.status_code == 401
    refresh = await client.post("/auth/api/refresh", json={"refresh_token": atacante_refresh})
    assert refresh.status_code == 401

    await db_session.refresh(victima)
    assert victima.is_verified is True


@pytest.mark.asyncio
async def test_callback_cuenta_verificada_conserva_su_password(client, db_session, test_user):
    patch_flow, patch_verify = _mock_google_exchange(test_user.email)
    response = await _callback(client, patch_flow, patch_verify)
    assert response.status_code == 303
    relogin = await client.post(
        "/auth/api/login", json={"email": test_user.email, "password": "test123"}
    )
    assert relogin.status_code == 200


@pytest.mark.asyncio
async def test_callback_email_de_google_sin_verificar_se_rechaza(client, db_session):
    patch_flow, _ = _mock_google_exchange("x@example.com")
    patch_verify = patch(
        "google.oauth2.id_token.verify_oauth2_token",
        return_value={"email": "x@example.com", "email_verified": False},
    )
    response = await _callback(client, patch_flow, patch_verify)
    assert "error=google_failed" in response.headers["location"]
    result = await db_session.execute(select(User).where(User.email == "x@example.com"))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_callback_encuentra_la_cuenta_sin_importar_mayusculas(client, db_session):
    from app.core.security import hash_password

    db_session.add(
        User(
            email="Ana.Perez@example.com",
            password_hash=hash_password("secreta1"),
            full_name="Ana",
            is_verified=True,
        )
    )
    await db_session.commit()

    patch_flow, patch_verify = _mock_google_exchange("ana.perez@example.com")
    response = await _callback(client, patch_flow, patch_verify)
    assert response.status_code == 303
    users = (await db_session.execute(select(User))).scalars().all()
    assert len(users) == 1


@pytest.mark.asyncio
async def test_register_no_permite_el_mismo_email_con_otras_mayusculas(client):
    body = {"email": "dup@example.com", "full_name": "Dup", "password": "secreta1", "accept_terms": True}
    assert (await client.post("/auth/api/register", json=body)).status_code == 201
    again = await client.post("/auth/api/register", json={**body, "email": "DUP@example.com"})
    assert again.status_code == 400

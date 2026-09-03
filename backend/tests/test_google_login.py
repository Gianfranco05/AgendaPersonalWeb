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

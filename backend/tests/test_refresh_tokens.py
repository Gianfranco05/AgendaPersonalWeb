from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.security import hash_refresh_token
from app.modules.auth.models import RefreshToken

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def logged_in(client, test_user):
    resp = await client.post("/auth/api/login", json={
        "email": "test@test.com",
        "password": "test123",
    })
    assert resp.status_code == 200
    return client, resp.json()


async def test_login_returns_refresh_token(logged_in):
    _, data = logged_in
    assert data["refresh_token"]
    assert data["access_token"] != data["refresh_token"]


async def test_register_returns_refresh_token(client):
    resp = await client.post("/auth/api/register", json={
        "email": "nuevo@test.com",
        "full_name": "Nuevo",
        "password": "password123",
    })
    assert resp.status_code == 201
    assert resp.json()["refresh_token"]


async def test_refresh_rotates_token(logged_in):
    client, data = logged_in
    old_refresh = data["refresh_token"]

    resp = await client.post("/auth/api/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200
    new = resp.json()
    assert new["access_token"]
    assert new["refresh_token"] != old_refresh


async def test_refreshed_access_token_authenticates(logged_in):
    client, data = logged_in
    resp = await client.post("/auth/api/refresh", json={"refresh_token": data["refresh_token"]})
    new_access = resp.json()["access_token"]

    client.cookies.clear()
    me = await client.get("/auth/api/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 200
    assert me.json()["email"] == "test@test.com"


async def test_refresh_works_from_cookie_without_body(logged_in):
    # Camino web: la cookie de refresh viaja sola, sin mandar el token en el body.
    client, _ = logged_in
    resp = await client.post("/auth/api/refresh", json={})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_invalid_refresh_token_rejected(client, test_user):
    resp = await client.post("/auth/api/refresh", json={"refresh_token": "no-existe"})
    assert resp.status_code == 401


async def test_missing_refresh_token_rejected(client, test_user):
    resp = await client.post("/auth/api/refresh", json={})
    assert resp.status_code == 401


async def test_expired_refresh_token_rejected(logged_in, db_session):
    client, data = logged_in
    raw = data["refresh_token"]

    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw))
    )
    token = result.scalar_one()
    token.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    await db_session.commit()

    resp = await client.post("/auth/api/refresh", json={"refresh_token": raw})
    assert resp.status_code == 401


async def test_reusing_rotated_token_revokes_all_sessions(logged_in, db_session):
    # Deteccion de robo: si aparece un token ya rotado, se asume que alguien lo
    # copio y se cierran todas las sesiones del usuario.
    client, data = logged_in
    old_refresh = data["refresh_token"]

    first = await client.post("/auth/api/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200
    new_refresh = first.json()["refresh_token"]

    replay = await client.post("/auth/api/refresh", json={"refresh_token": old_refresh})
    assert replay.status_code == 401

    # El token nuevo tambien queda muerto tras detectar el reuse.
    after = await client.post("/auth/api/refresh", json={"refresh_token": new_refresh})
    assert after.status_code == 401

    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.user_id == str(data["id"]))
    )
    assert all(t.revoked_at is not None for t in result.scalars().all())


async def test_logout_revokes_refresh_token(logged_in):
    client, data = logged_in
    raw = data["refresh_token"]

    logout = await client.post("/auth/api/logout")
    assert logout.status_code == 200

    resp = await client.post("/auth/api/refresh", json={"refresh_token": raw})
    assert resp.status_code == 401


async def test_sessions_lists_active_session(logged_in):
    client, _ = logged_in
    resp = await client.get("/auth/api/sessions")
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) == 1
    assert "id" in sessions[0]


async def test_revoking_session_kills_its_refresh_token(logged_in):
    client, data = logged_in
    raw = data["refresh_token"]

    sessions = (await client.get("/auth/api/sessions")).json()
    session_id = sessions[0]["id"]

    delete_resp = await client.delete(f"/auth/api/sessions/{session_id}")
    assert delete_resp.status_code == 204

    resp = await client.post("/auth/api/refresh", json={"refresh_token": raw})
    assert resp.status_code == 401


async def test_user_cannot_revoke_another_users_session(logged_in):
    client, _ = logged_in
    session_id = (await client.get("/auth/api/sessions")).json()[0]["id"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as other:
        await other.post("/auth/api/register", json={
            "email": "otro@test.com",
            "full_name": "Otro",
            "password": "password123",
        })
        resp = await other.delete(f"/auth/api/sessions/{session_id}")
        assert resp.status_code == 404

        # Y no ve la sesion ajena en su propio listado.
        own = (await other.get("/auth/api/sessions")).json()
        assert all(s["id"] != session_id for s in own)


async def test_second_login_creates_second_session(logged_in):
    client, _ = logged_in

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as second_device:
        await second_device.post("/auth/api/login", json={
            "email": "test@test.com",
            "password": "test123",
        })

    sessions = (await client.get("/auth/api/sessions")).json()
    assert len(sessions) == 2

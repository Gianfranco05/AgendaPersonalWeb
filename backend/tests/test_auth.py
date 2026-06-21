import pytest
from app.core.security import hash_password
from app.modules.auth.models import User


@pytest.mark.asyncio
async def test_login_success(client, test_user):
    response = await client.post("/auth/login", data={
        "email": "test@test.com",
        "password": "test123",
    })
    assert response.status_code == 303
    assert response.headers["location"] == "/finanzas/"
    assert "vida_token" in response.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_login_wrong_password(client, test_user):
    response = await client.post("/auth/login", data={
        "email": "test@test.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 400
    assert "incorrectos" in response.text


@pytest.mark.asyncio
async def test_login_wrong_email(client, test_user):
    response = await client.post("/auth/login", data={
        "email": "noexiste@test.com",
        "password": "test123",
    })
    assert response.status_code == 400
    assert "incorrectos" in response.text


@pytest.mark.asyncio
async def test_register_success(client, db_session):
    response = await client.post("/auth/register", data={
        "email": "new@test.com",
        "full_name": "New User",
        "password": "newpassword123",
        "password_confirm": "newpassword123",
    })
    assert response.status_code == 303
    assert response.headers["location"] == "/finanzas/"
    assert "vida_token" in response.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_register_duplicate_email(client, test_user):
    response = await client.post("/auth/register", data={
        "email": "test@test.com",
        "full_name": "Another User",
        "password": "another123",
        "password_confirm": "another123",
    })
    assert response.status_code == 400
    assert "ya está registrado" in response.text


@pytest.mark.asyncio
async def test_register_password_mismatch(client):
    response = await client.post("/auth/register", data={
        "email": "mismatch@test.com",
        "full_name": "Mismatch",
        "password": "password123",
        "password_confirm": "different",
    })
    assert response.status_code == 400
    assert "no coinciden" in response.text


@pytest.mark.asyncio
async def test_register_short_password(client):
    response = await client.post("/auth/register", data={
        "email": "short@test.com",
        "full_name": "Short",
        "password": "1234567",
        "password_confirm": "1234567",
    })
    assert response.status_code == 400
    assert "8 caracteres" in response.text


@pytest.mark.asyncio
async def test_logout(client, test_user):
    await client.post("/auth/login", data={
        "email": "test@test.com",
        "password": "test123",
    })
    response = await client.post("/auth/logout")
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login"
    set_cookie = response.headers.get("set-cookie", "")
    assert "vida_token=" in set_cookie
    assert "Max-Age=0" in set_cookie or 'max-age=0' in set_cookie.lower() or "expires=Thu, 01 Jan 1970" in set_cookie


@pytest.mark.asyncio
async def test_protected_route_without_auth(client):
    response = await client.get("/finanzas/", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_dashboard_with_auth(auth_client):
    response = await auth_client.get("/finanzas/")
    assert response.status_code == 200
    assert "Dashboard" in response.text or "Vida Personal" in response.text


@pytest.mark.asyncio
async def test_login_page_get(client):
    response = await client.get("/auth/login")
    assert response.status_code == 200
    assert "Iniciar Sesion" in response.text


@pytest.mark.asyncio
async def test_register_page_get(client):
    response = await client.get("/auth/register")
    assert response.status_code == 200
    assert "Crear Cuenta" in response.text

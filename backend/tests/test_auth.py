import pytest
from app.config import settings
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
async def test_legacy_register_post_redirige_a_la_spa_y_no_crea_usuario(client, db_session):
    """El registro HTML se apago: crea cuentas sin Terminos ni declaracion de
    edad. Redirige a /register de la SPA sin leer ni guardar nada."""
    from sqlalchemy import select

    response = await client.post("/auth/register", data={
        "email": "new@test.com",
        "full_name": "New User",
        "password": "newpassword123",
        "password_confirm": "newpassword123",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"{settings.PUBLIC_BASE_URL.rstrip('/')}/register"
    assert "vida_token" not in response.headers.get("set-cookie", "")
    result = await db_session.execute(select(User).where(User.email == "new@test.com"))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_legacy_register_get_redirige_a_la_spa(client):
    response = await client.get("/auth/register", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"{settings.PUBLIC_BASE_URL.rstrip('/')}/register"


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
    assert "Dashboard" in response.text or "Can_cen" in response.text


@pytest.mark.asyncio
async def test_login_page_get(client):
    response = await client.get("/auth/login")
    assert response.status_code == 200
    assert "Iniciar Sesion" in response.text


@pytest.mark.asyncio
async def test_legacy_login_html_rechaza_usuario_inactivo(client, db_session, test_user):
    test_user.is_active = False
    await db_session.commit()
    response = await client.post(
        "/auth/login", data={"email": "test@test.com", "password": "test123"}
    )
    assert response.status_code == 403
    assert "vida_token" not in response.cookies

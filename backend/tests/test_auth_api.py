import pytest


@pytest.mark.asyncio
async def test_api_login_returns_access_token(client, test_user):
    response = await client.post("/auth/api/login", json={
        "email": "test@test.com",
        "password": "test123",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@test.com"
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_api_register_returns_access_token(client):
    response = await client.post("/auth/api/register", json={
        "email": "mobile@test.com",
        "full_name": "Mobile User",
        "password": "mobilepass123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "mobile@test.com"
    assert "access_token" in data


@pytest.mark.asyncio
async def test_bearer_token_authenticates_protected_endpoint(client, test_user):
    login_resp = await client.post("/auth/api/login", json={
        "email": "test@test.com",
        "password": "test123",
    })
    token = login_resp.json()["access_token"]

    # httpx guarda la cookie que devolvio el login; la limpiamos para probar
    # el camino de Bearer puro, como lo usaria la app movil (sin cookie jar).
    client.cookies.clear()

    response = await client.get(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_bearer_token_invalid_is_rejected(client):
    response = await client.get(
        "/api/v1/tasks",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cookie_still_works_without_bearer_header(auth_client):
    # auth_client ya tiene la cookie seteada (flujo web existente) — confirma
    # que agregar soporte Bearer no rompe el camino de cookie.
    response = await auth_client.get("/api/v1/tasks")
    assert response.status_code == 200

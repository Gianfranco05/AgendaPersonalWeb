import pytest


@pytest.mark.asyncio
async def test_login_page(client):
    response = await client.get("/auth/login")
    assert response.status_code == 200
    assert "Iniciar" in response.text or "login" in response.text.lower()


@pytest.mark.asyncio
async def test_register_page_redirects_to_spa(client):
    response = await client.get("/auth/register", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].endswith("/register")


@pytest.mark.asyncio
async def test_finanzas_redirects_without_auth(client):
    response = await client.get("/finanzas/", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_finanzas_transacciones_redirects_without_auth(client):
    response = await client.get("/finanzas/transacciones", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_finanzas_categorias_redirects_without_auth(client):
    response = await client.get("/finanzas/categorias", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_finanzas_reportes_redirects_without_auth(client):
    response = await client.get("/finanzas/reportes", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_finanzas_dashboard_with_auth(auth_client):
    response = await auth_client.get("/finanzas/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_finanzas_transacciones_with_auth(auth_client):
    response = await auth_client.get("/finanzas/transacciones")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_finanzas_categorias_with_auth(auth_client):
    response = await auth_client.get("/finanzas/categorias")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_finanzas_reportes_with_auth(auth_client):
    response = await auth_client.get("/finanzas/reportes")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_anotaciones_redirects_without_auth(client):
    response = await client.get("/anotaciones/", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_anotaciones_nueva_redirects_without_auth(client):
    response = await client.get("/anotaciones/nueva", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_anotaciones_etiquetas_redirects_without_auth(client):
    response = await client.get("/anotaciones/etiquetas", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_anotaciones_with_auth(auth_client):
    response = await auth_client.get("/anotaciones/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_anotaciones_nueva_with_auth(auth_client):
    response = await auth_client.get("/anotaciones/nueva")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_anotaciones_etiquetas_with_auth(auth_client):
    response = await auth_client.get("/anotaciones/etiquetas")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_eventos_redirects_without_auth(client):
    response = await client.get("/eventos/", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_eventos_nuevo_redirects_without_auth(client):
    response = await client.get("/eventos/nuevo", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_eventos_with_auth(auth_client):
    response = await auth_client.get("/eventos/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_eventos_nuevo_with_auth(auth_client):
    response = await auth_client.get("/eventos/nuevo")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_metas_redirects_without_auth(client):
    response = await client.get("/metas/", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_metas_nueva_redirects_without_auth(client):
    response = await client.get("/metas/nueva", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_metas_with_auth(auth_client):
    response = await auth_client.get("/metas/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_metas_nueva_with_auth(auth_client):
    response = await auth_client.get("/metas/nueva")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ajustes_redirects_without_auth(client):
    response = await client.get("/ajustes/", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_ajustes_with_auth(auth_client):
    response = await auth_client.get("/ajustes/")
    assert response.status_code == 200

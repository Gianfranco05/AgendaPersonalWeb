import pytest
from sqlalchemy import select
from app.modules.ajustes.models import UserPreference


@pytest.mark.asyncio
async def test_get_preferences(auth_client):
    response = await auth_client.get("/ajustes/")
    assert response.status_code == 200
    assert "Ajustes" in response.text


@pytest.mark.asyncio
async def test_update_preferences(auth_client, db_session):
    response = await auth_client.post("/ajustes/", data={
        "currency": "USD",
        "theme_color": "blue",
        "date_format": "MM/DD/YYYY",
    })
    assert response.status_code == 303

    result = await db_session.execute(
        select(UserPreference).where(UserPreference.currency == "USD")
    )
    prefs = result.scalar_one_or_none()
    assert prefs is not None
    assert prefs.theme_color == "blue"
    assert prefs.date_format == "MM/DD/YYYY"


@pytest.mark.asyncio
async def test_preferences_creates_default(auth_client, db_session):
    response = await auth_client.get("/ajustes/")
    assert response.status_code == 200

    result = await db_session.execute(select(UserPreference))
    prefs = result.scalar_one_or_none()
    assert prefs is not None
    assert prefs.currency == "ARS"
    assert prefs.theme_color == "violet"


@pytest.mark.asyncio
async def test_preferences_requires_auth(client):
    response = await client.get("/ajustes/", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_api_preferences(auth_client):
    await auth_client.get("/ajustes/")

    response = await auth_client.get("/ajustes/api/preferences")
    assert response.status_code == 200
    data = response.json()
    assert "currency" in data
    assert "theme_color" in data


@pytest.mark.asyncio
async def test_update_preferences_invalid_theme(auth_client, db_session):
    response = await auth_client.post("/ajustes/", data={
        "currency": "ARS",
        "theme_color": "invalid_color",
        "date_format": "DD/MM/YYYY",
    })
    assert response.status_code == 303

    result = await db_session.execute(select(UserPreference))
    prefs = result.scalar_one_or_none()
    assert prefs is not None
    assert prefs.theme_color == "violet"


@pytest.mark.asyncio
async def test_api_v1_settings_get_and_update(api_auth_client):
    get_resp = await api_auth_client.get("/api/v1/settings")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert "currency" in data
    assert "theme_color" in data
    assert "date_format" in data
    assert "google_calendar_id" in data

    update_resp = await api_auth_client.put("/api/v1/settings", json={
        "currency": "USD",
        "theme_color": "blue",
        "date_format": "MM/DD/YYYY",
    })
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["currency"] == "USD"
    assert updated["theme_color"] == "blue"
    assert updated["date_format"] == "MM/DD/YYYY"

    get_updated = await api_auth_client.get("/api/v1/settings")
    assert get_updated.json()["currency"] == "USD"


@pytest.mark.asyncio
async def test_api_v1_settings_google_not_connected_by_default(api_auth_client):
    response = await api_auth_client.get("/api/v1/settings")
    assert response.status_code == 200
    assert response.json()["google_connected"] is False


@pytest.mark.asyncio
async def test_api_v1_google_sync_requires_connection(api_auth_client):
    response = await api_auth_client.post("/api/v1/settings/google/sync")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_api_v1_google_disconnect_is_idempotent(api_auth_client):
    response = await api_auth_client.post("/api/v1/settings/google/disconnect")
    assert response.status_code == 200
    assert response.json()["google_connected"] is False


@pytest.mark.asyncio
async def test_api_v1_settings_requires_auth(client):
    response = await client.get("/api/v1/settings")
    assert response.status_code == 401

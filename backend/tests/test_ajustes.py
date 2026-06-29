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

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


# ── Cotizaciones y toggle de inversiones (/api/v1/settings) ─────────────────


@pytest.mark.asyncio
async def test_settings_defaults_de_inversiones(api_auth_client):
    data = (await api_auth_client.get("/api/v1/settings")).json()
    assert data["fx_usd_ars"] is None
    assert data["fx_eur_ars"] is None
    assert data["fx_rates_updated_at"] is None
    assert data["include_investments_in_balance"] is False


@pytest.mark.asyncio
async def test_settings_setear_cotizacion_dolar(api_auth_client):
    resp = await api_auth_client.put("/api/v1/settings", json={"fx_usd_ars": 1450.50})
    assert resp.status_code == 200
    data = resp.json()
    assert data["fx_usd_ars"] == "1450.5000"
    assert data["fx_rates_updated_at"] is not None
    assert (await api_auth_client.get("/api/v1/settings")).json()["fx_usd_ars"] == "1450.5000"


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [0, -1, "-0.5", 10000000, "1450.12345", "abc"])
async def test_settings_cotizacion_invalida_es_422_y_conserva_la_anterior(api_auth_client, value):
    await api_auth_client.put("/api/v1/settings", json={"fx_usd_ars": "1000"})
    resp = await api_auth_client.put("/api/v1/settings", json={"fx_usd_ars": value})
    assert resp.status_code == 422
    assert (await api_auth_client.get("/api/v1/settings")).json()["fx_usd_ars"] == "1000.0000"


@pytest.mark.asyncio
async def test_settings_cotizacion_en_el_borde_se_acepta(api_auth_client):
    resp = await api_auth_client.put(
        "/api/v1/settings", json={"fx_usd_ars": "9999999.9999", "fx_eur_ars": "0.0001"}
    )
    assert resp.status_code == 200
    assert resp.json()["fx_usd_ars"] == "9999999.9999"
    assert resp.json()["fx_eur_ars"] == "0.0001"


@pytest.mark.asyncio
async def test_settings_null_borra_la_cotizacion(api_auth_client):
    await api_auth_client.put("/api/v1/settings", json={"fx_usd_ars": "1000", "fx_eur_ars": "1100"})
    data = (await api_auth_client.put("/api/v1/settings", json={"fx_eur_ars": None})).json()
    assert data["fx_eur_ars"] is None
    assert data["fx_usd_ars"] == "1000.0000"
    assert data["fx_rates_updated_at"] is not None
    # Sin ninguna cotizacion cargada no tiene sentido una fecha de actualizacion.
    cleared = (await api_auth_client.put("/api/v1/settings", json={"fx_usd_ars": None})).json()
    assert cleared["fx_usd_ars"] is None and cleared["fx_rates_updated_at"] is None


@pytest.mark.asyncio
async def test_settings_fx_rates_updated_at_solo_cambia_si_cambia_una_cotizacion(api_auth_client):
    first = (await api_auth_client.put("/api/v1/settings", json={"fx_usd_ars": "1000"})).json()
    stamp = first["fx_rates_updated_at"]

    other = (await api_auth_client.put("/api/v1/settings", json={"theme_color": "blue"})).json()
    assert other["fx_rates_updated_at"] == stamp

    same = (await api_auth_client.put("/api/v1/settings", json={"fx_usd_ars": "1000.00"})).json()
    assert same["fx_rates_updated_at"] == stamp

    toggle = (
        await api_auth_client.put("/api/v1/settings", json={"include_investments_in_balance": True})
    ).json()
    assert toggle["fx_rates_updated_at"] == stamp


@pytest.mark.asyncio
async def test_settings_el_cliente_no_puede_fijar_fx_rates_updated_at(api_auth_client):
    resp = await api_auth_client.put(
        "/api/v1/settings", json={"fx_usd_ars": "1000", "fx_rates_updated_at": "2020-01-01T00:00:00Z"}
    )
    assert resp.status_code == 200
    assert not resp.json()["fx_rates_updated_at"].startswith("2020")


@pytest.mark.asyncio
async def test_settings_toggle_de_inversiones(api_auth_client):
    on = (await api_auth_client.put("/api/v1/settings", json={"include_investments_in_balance": True})).json()
    assert on["include_investments_in_balance"] is True
    # null no apaga ni rompe la columna (no admite null).
    kept = await api_auth_client.put("/api/v1/settings", json={"include_investments_in_balance": None})
    assert kept.status_code == 200 and kept.json()["include_investments_in_balance"] is True
    off = (await api_auth_client.put("/api/v1/settings", json={"include_investments_in_balance": False})).json()
    assert off["include_investments_in_balance"] is False


# ── Tutorial de bienvenida (onboarding_version_seen) ────────────────────────


@pytest.mark.asyncio
async def test_settings_onboarding_default_es_cero(api_auth_client):
    data = (await api_auth_client.get("/api/v1/settings")).json()
    assert data["onboarding_version_seen"] == 0


@pytest.mark.asyncio
async def test_settings_onboarding_marcar_como_visto(api_auth_client):
    resp = await api_auth_client.put("/api/v1/settings", json={"onboarding_version_seen": 1})
    assert resp.status_code == 200 and resp.json()["onboarding_version_seen"] == 1
    assert (await api_auth_client.get("/api/v1/settings")).json()["onboarding_version_seen"] == 1


@pytest.mark.asyncio
async def test_settings_onboarding_nunca_baja(api_auth_client):
    await api_auth_client.put("/api/v1/settings", json={"onboarding_version_seen": 2})
    resp = await api_auth_client.put("/api/v1/settings", json={"onboarding_version_seen": 1})
    assert resp.status_code == 200 and resp.json()["onboarding_version_seen"] == 2
    zero = await api_auth_client.put("/api/v1/settings", json={"onboarding_version_seen": 0})
    assert zero.json()["onboarding_version_seen"] == 2


@pytest.mark.asyncio
async def test_settings_onboarding_null_se_ignora(api_auth_client):
    await api_auth_client.put("/api/v1/settings", json={"onboarding_version_seen": 1})
    resp = await api_auth_client.put("/api/v1/settings", json={"onboarding_version_seen": None})
    assert resp.status_code == 200 and resp.json()["onboarding_version_seen"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [-1, 1001, 5000, "x", 1.5])
async def test_settings_onboarding_invalido_es_422(api_auth_client, value):
    resp = await api_auth_client.put("/api/v1/settings", json={"onboarding_version_seen": value})
    assert resp.status_code == 422
    assert (await api_auth_client.get("/api/v1/settings")).json()["onboarding_version_seen"] == 0


@pytest.mark.asyncio
async def test_settings_onboarding_no_se_pisa_al_guardar_otros_ajustes(api_auth_client):
    await api_auth_client.put("/api/v1/settings", json={"onboarding_version_seen": 1})
    other = await api_auth_client.put("/api/v1/settings", json={"theme_color": "blue"})
    assert other.json()["onboarding_version_seen"] == 1


@pytest.mark.asyncio
async def test_settings_onboarding_aislado_entre_usuarios(client, api_auth_client):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    await api_auth_client.put("/api/v1/settings", json={"onboarding_version_seen": 1})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as other:
        reg = await other.post("/auth/api/register", json={
            "email": "otro@test.com",
            "full_name": "Otro",
            "password": "testpass123",
            "accept_terms": True,
            "confirm_age": True,
        })
        assert reg.status_code == 201, reg.text
        assert (await other.get("/api/v1/settings")).json()["onboarding_version_seen"] == 0
        await other.put("/api/v1/settings", json={"onboarding_version_seen": 3})

    assert (await api_auth_client.get("/api/v1/settings")).json()["onboarding_version_seen"] == 1


@pytest.mark.asyncio
async def test_export_de_cuenta_incluye_onboarding_version_seen(api_auth_client):
    await api_auth_client.put("/api/v1/settings", json={"onboarding_version_seen": 1})
    data = (await api_auth_client.get("/api/v1/me/export")).json()
    assert data["user_preferences"][0]["onboarding_version_seen"] == 1

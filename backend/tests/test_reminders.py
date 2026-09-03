import pytest

pytestmark = pytest.mark.asyncio


async def _crear_recordatorio(client, message="Tomar agua", hour=9, **extra):
    resp = await client.post(
        "/api/v1/reminders", json={"message": message, "hour": hour, **extra}
    )
    assert resp.status_code == 201
    return resp.json()


async def test_reminders_require_auth(client):
    assert (await client.get("/api/v1/reminders")).status_code == 401


async def test_create_uses_sensible_defaults(api_auth_client):
    reminder = await _crear_recordatorio(api_auth_client)
    assert reminder["minute"] == 0  # default
    assert reminder["icon"] == "🔔"  # default
    assert reminder["enabled"] is True  # default


async def test_create_with_custom_icon_and_minute(api_auth_client):
    reminder = await _crear_recordatorio(
        api_auth_client, message="Estirar", hour=15, minute=30, icon="🧘"
    )
    assert reminder["minute"] == 30
    assert reminder["icon"] == "🧘"


async def test_create_rejects_an_invalid_hour(api_auth_client):
    resp = await api_auth_client.post(
        "/api/v1/reminders", json={"message": "X", "hour": 24}
    )
    assert resp.status_code == 422


async def test_create_rejects_an_invalid_minute(api_auth_client):
    resp = await api_auth_client.post(
        "/api/v1/reminders", json={"message": "X", "hour": 9, "minute": 60}
    )
    assert resp.status_code == 422


async def test_create_rejects_an_empty_message(api_auth_client):
    resp = await api_auth_client.post(
        "/api/v1/reminders", json={"message": "", "hour": 9}
    )
    assert resp.status_code == 422


async def test_create_rejects_an_oversized_message(api_auth_client):
    resp = await api_auth_client.post(
        "/api/v1/reminders", json={"message": "x" * 201, "hour": 9}
    )
    assert resp.status_code == 422


async def test_list_is_sorted_by_time(api_auth_client):
    tarde = await _crear_recordatorio(api_auth_client, "Tarde", hour=20)
    temprano = await _crear_recordatorio(api_auth_client, "Temprano", hour=7)

    reminders = (await api_auth_client.get("/api/v1/reminders")).json()
    assert [r["id"] for r in reminders] == [temprano["id"], tarde["id"]]


async def test_update_reminder(api_auth_client):
    reminder = await _crear_recordatorio(api_auth_client)
    resp = await api_auth_client.patch(
        f"/api/v1/reminders/{reminder['id']}",
        json={"message": "Cargar hábitos", "hour": 21, "enabled": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Cargar hábitos"
    assert data["hour"] == 21
    assert data["enabled"] is False


async def test_update_can_disable_without_touching_other_fields(api_auth_client):
    reminder = await _crear_recordatorio(api_auth_client, message="Fijo", hour=9)
    resp = await api_auth_client.patch(
        f"/api/v1/reminders/{reminder['id']}", json={"enabled": False}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    assert data["message"] == "Fijo"
    assert data["hour"] == 9


async def test_update_unknown_reminder_is_404(api_auth_client):
    resp = await api_auth_client.patch("/api/v1/reminders/nope", json={"message": "X"})
    assert resp.status_code == 404


async def test_delete_reminder(api_auth_client):
    reminder = await _crear_recordatorio(api_auth_client)
    assert (
        await api_auth_client.delete(f"/api/v1/reminders/{reminder['id']}")
    ).status_code == 204
    assert (await api_auth_client.get("/api/v1/reminders")).json() == []


async def test_delete_unknown_reminder_is_404(api_auth_client):
    assert (await api_auth_client.delete("/api/v1/reminders/nope")).status_code == 404


async def test_reminders_of_another_user_are_not_reachable(api_auth_client, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User
    from app.modules.recordatorios.service import ReminderService

    otro = User(
        email="otro_reminders@test.com",
        password_hash=hash_password("test123"),
        full_name="Otro",
        is_active=True,
    )
    db_session.add(otro)
    await db_session.commit()
    ajeno = await ReminderService(db_session).create_reminder(otro.id, "Ajeno", 9)

    assert (await api_auth_client.get("/api/v1/reminders")).json() == []
    assert (
        await api_auth_client.patch(f"/api/v1/reminders/{ajeno.id}", json={"message": "Hackeado"})
    ).status_code == 404
    assert (await api_auth_client.delete(f"/api/v1/reminders/{ajeno.id}")).status_code == 404

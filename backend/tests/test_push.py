from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.modules.push.models import PushToken
from app.modules.recordatorios.models import Reminder
from app.modules.recordatorios.scheduler import should_fire


# ── Registro de push token ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_push_token(api_auth_client, db_session, test_user):
    response = await api_auth_client.post("/api/v1/push/register", json={
        "token": "ExponentPushToken[abc123]",
        "device_info": "Pixel 8",
    })
    assert response.status_code == 204

    result = await db_session.execute(
        select(PushToken).where(PushToken.user_id == test_user.id)
    )
    token = result.scalar_one()
    assert token.token == "ExponentPushToken[abc123]"
    assert token.device_info == "Pixel 8"


@pytest.mark.asyncio
async def test_register_push_token_requires_auth(client):
    response = await client.post("/api/v1/push/register", json={"token": "x"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_reassigns_token_on_account_switch(api_auth_client, db_session, test_user):
    """Si el mismo telefono cambia de cuenta (logout + login de otra
    persona), el token tiene que dejar de apuntar a la cuenta vieja — sin
    esto, la cuenta vieja seguiria recibiendo push de un dispositivo que ya
    no es suyo."""
    from app.core.security import hash_password
    from app.modules.auth.models import User

    otro = User(
        email="otro-dispositivo@example.com",
        password_hash=hash_password("otra-password"),
        full_name="Otro",
        is_verified=True,
    )
    db_session.add(otro)
    await db_session.commit()

    await api_auth_client.post("/api/v1/push/register", json={"token": "ExponentPushToken[shared]"})

    # Logueado como test_user en la fixture; simulamos el registro de "otro"
    # llamando al service directamente (no hay una segunda cookie jar acá).
    from app.modules.push.service import PushService
    await PushService(db_session).register(str(otro.id), "ExponentPushToken[shared]")

    result = await db_session.execute(
        select(PushToken).where(PushToken.token == "ExponentPushToken[shared]")
    )
    tokens = result.scalars().all()
    assert len(tokens) == 1
    assert tokens[0].user_id == str(otro.id)


@pytest.mark.asyncio
async def test_unregister_push_token(api_auth_client, db_session, test_user):
    await api_auth_client.post("/api/v1/push/register", json={"token": "ExponentPushToken[bye]"})

    response = await api_auth_client.request(
        "DELETE", "/api/v1/push/register", json={"token": "ExponentPushToken[bye]"}
    )
    assert response.status_code == 204

    result = await db_session.execute(
        select(PushToken).where(PushToken.token == "ExponentPushToken[bye]")
    )
    assert result.scalar_one_or_none() is None


# ── Logica de disparo del scheduler ─────────────────────────────────────────

def _reminder(**overrides) -> Reminder:
    defaults = dict(
        id="r1",
        user_id="u1",
        message="Tomar agua",
        icon="💧",
        hour=9,
        minute=0,
        timezone_offset_minutes=-180,  # UTC-3
        enabled=True,
    )
    defaults.update(overrides)
    return Reminder(**defaults)


def test_should_fire_matches_local_hour_and_minute():
    # 12:00 UTC == 09:00 en UTC-3
    now_utc = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
    assert should_fire(_reminder(), now_utc) is True


def test_should_fire_false_outside_the_minute():
    now_utc = datetime(2026, 9, 21, 12, 5, tzinfo=timezone.utc)
    assert should_fire(_reminder(), now_utc) is False


def test_should_fire_false_when_disabled():
    now_utc = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
    assert should_fire(_reminder(enabled=False), now_utc) is False


def test_should_fire_false_without_timezone():
    now_utc = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
    assert should_fire(_reminder(timezone_offset_minutes=None), now_utc) is False


def test_should_fire_false_if_already_sent_today():
    from app.modules.recordatorios import scheduler

    now_utc = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
    reminder = _reminder()
    local_date = (now_utc + timedelta(minutes=reminder.timezone_offset_minutes)).date()
    scheduler._sent_today[reminder.id] = local_date
    try:
        assert should_fire(reminder, now_utc) is False
    finally:
        scheduler._sent_today.clear()

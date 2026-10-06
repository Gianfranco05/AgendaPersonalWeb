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


# ── Desregistro: solo el token propio ───────────────────────────────────────

@pytest.mark.asyncio
async def test_unregister_no_borra_el_token_de_otro_usuario(api_auth_client, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User

    otro = User(email="otro@test.com", password_hash=hash_password("x12345"), full_name="Otro")
    db_session.add(otro)
    await db_session.commit()
    db_session.add(PushToken(user_id=otro.id, token="ExponentPushToken[ajeno]"))
    await db_session.commit()

    response = await api_auth_client.request(
        "DELETE", "/api/v1/push/register", json={"token": "ExponentPushToken[ajeno]"}
    )
    assert response.status_code == 204

    result = await db_session.execute(
        select(PushToken).where(PushToken.token == "ExponentPushToken[ajeno]")
    )
    assert result.scalar_one().user_id == otro.id


# ── Canal de Android ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_to_user_incluye_el_channel_id_de_la_app(db_session, test_user, monkeypatch):
    from unittest.mock import MagicMock

    from app.modules.push import service as push_service

    db_session.add(PushToken(user_id=test_user.id, token="ExponentPushToken[t1]"))
    await db_session.commit()

    sent = {}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json):
            sent["json"] = json
            response = MagicMock()
            response.json.return_value = {"data": [{"status": "ok"}]}
            return response

    monkeypatch.setattr(push_service.httpx, "AsyncClient", FakeClient)
    await push_service.PushService(db_session).send_to_user(test_user.id, "t", "b")

    # Tiene que coincidir con ANDROID_CHANNEL_ID de la app mobile
    # (src/lib/notifications.ts); si no, la push cae en el canal por defecto.
    assert sent["json"][0]["channelId"] == "recordatorios"


# ── Scheduler: duplicados entre workers y minutos salteados ────────────────

@pytest.mark.asyncio
async def test_claim_en_redis_solo_lo_gana_un_proceso(monkeypatch):
    from datetime import date

    from app.config import settings
    from app.modules.recordatorios import scheduler

    claimed_keys = set()

    class FakeRedis:
        async def set(self, key, value, nx=False, ex=None):
            if nx and key in claimed_keys:
                return None
            claimed_keys.add(key)
            return True

    monkeypatch.setattr(settings, "REDIS_URL", "redis://fake")
    monkeypatch.setattr(scheduler, "_redis_client", FakeRedis())

    # Dos workers (dos procesos) intentan reclamar el mismo disparo.
    assert await scheduler._claim_in_redis("r1", date(2026, 9, 21)) is True
    assert await scheduler._claim_in_redis("r1", date(2026, 9, 21)) is False
    # Otro dia u otro recordatorio no se pisa.
    assert await scheduler._claim_in_redis("r1", date(2026, 9, 22)) is True
    assert await scheduler._claim_in_redis("r2", date(2026, 9, 21)) is True


@pytest.mark.asyncio
async def test_claim_sin_redis_o_con_redis_caido_no_pierde_el_recordatorio(monkeypatch):
    from datetime import date

    from app.config import settings
    from app.modules.recordatorios import scheduler

    monkeypatch.setattr(settings, "REDIS_URL", "")
    assert await scheduler._claim_in_redis("r1", date(2026, 9, 21)) is True

    class BrokenRedis:
        async def set(self, *a, **k):
            raise ConnectionError("redis caido")

    monkeypatch.setattr(settings, "REDIS_URL", "redis://fake")
    monkeypatch.setattr(scheduler, "_redis_client", BrokenRedis())
    assert await scheduler._claim_in_redis("r1", date(2026, 9, 21)) is True


def test_minutes_to_check_recupera_el_minuto_saltado(monkeypatch):
    from app.modules.recordatorios import scheduler

    monkeypatch.setattr(scheduler, "_last_checked_minute", None)
    first = scheduler._minutes_to_check(datetime(2026, 9, 21, 12, 0, 59, tzinfo=timezone.utc))
    assert first == [datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)]

    # El ciclo siguiente llega tarde y se salteo el minuto 12:01.
    second = scheduler._minutes_to_check(datetime(2026, 9, 21, 12, 2, 0, tzinfo=timezone.utc))
    assert second == [
        datetime(2026, 9, 21, 12, 1, tzinfo=timezone.utc),
        datetime(2026, 9, 21, 12, 2, tzinfo=timezone.utc),
    ]


def test_minutes_to_check_no_dispara_recordatorios_viejos_tras_una_caida(monkeypatch):
    from app.modules.recordatorios import scheduler

    monkeypatch.setattr(
        scheduler, "_last_checked_minute", datetime(2026, 9, 21, 8, 0, tzinfo=timezone.utc)
    )
    minutes = scheduler._minutes_to_check(datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc))
    assert len(minutes) == scheduler.MAX_CATCHUP_MINUTES + 1
    assert minutes[-1] == datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)

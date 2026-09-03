from datetime import datetime, timedelta, timezone

import pytest

from app.modules.focus.models import FocusSession
from app.modules.focus.service import FocusService

pytestmark = pytest.mark.asyncio


async def _seed(db_session, user_id: str, started_at: datetime, duration: int | None):
    session = FocusSession(
        user_id=user_id,
        started_at=started_at,
        ended_at=started_at + timedelta(seconds=duration) if duration is not None else None,
        duration_seconds=duration,
    )
    db_session.add(session)
    await db_session.commit()
    return session


# ── Auth ─────────────────────────────────────────────────────────────────────

async def test_focus_endpoints_require_auth(client):
    assert (await client.get("/api/v1/focus/summary")).status_code == 401
    assert (await client.post("/api/v1/focus/start")).status_code == 401
    assert (await client.post("/api/v1/focus/stop")).status_code == 401
    assert (await client.get("/api/v1/focus/sessions")).status_code == 401


# ── Start / stop ─────────────────────────────────────────────────────────────

async def test_start_creates_a_running_session(api_auth_client):
    resp = await api_auth_client.post("/api/v1/focus/start", json={"label": "Escribir informe"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ended_at"] is None
    assert data["duration_seconds"] is None
    assert data["label"] == "Escribir informe"


async def test_start_twice_returns_the_same_session(api_auth_client):
    # Doble tap en el celular: no puede abrir dos sesiones en paralelo.
    first = (await api_auth_client.post("/api/v1/focus/start")).json()
    second = (await api_auth_client.post("/api/v1/focus/start")).json()
    assert first["id"] == second["id"]

    sessions = (await api_auth_client.get("/api/v1/focus/sessions")).json()
    assert len(sessions) == 1


async def test_stop_closes_the_session_and_computes_duration(
    api_auth_client, db_session, test_user
):
    started = datetime.now(timezone.utc) - timedelta(minutes=25)
    await _seed(db_session, test_user.id, started, None)

    resp = await api_auth_client.post("/api/v1/focus/stop")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ended_at"] is not None
    # ~25 minutos; se deja margen por lo que tarda el test en si.
    assert 1490 <= data["duration_seconds"] <= 1510


async def test_stop_without_an_active_session_is_404(api_auth_client):
    assert (await api_auth_client.post("/api/v1/focus/stop")).status_code == 404


async def test_start_after_stop_opens_a_new_session(api_auth_client):
    first = (await api_auth_client.post("/api/v1/focus/start")).json()
    await api_auth_client.post("/api/v1/focus/stop")
    second = (await api_auth_client.post("/api/v1/focus/start")).json()
    assert first["id"] != second["id"]


# ── Resumen ──────────────────────────────────────────────────────────────────

async def test_summary_counts_only_closed_sessions(api_auth_client, db_session, test_user):
    now = datetime.now(timezone.utc)
    await _seed(db_session, test_user.id, now - timedelta(hours=2), 3600)
    await _seed(db_session, test_user.id, now - timedelta(minutes=10), None)  # corriendo

    data = (await api_auth_client.get("/api/v1/focus/summary")).json()
    # La sesion en curso no suma: esos segundos los cuenta el cliente, que tiene
    # el reloj andando.
    assert data["today_seconds"] == 3600
    assert data["active"] is not None
    assert data["active"]["duration_seconds"] is None


async def test_summary_excludes_sessions_from_previous_days(
    api_auth_client, db_session, test_user
):
    now = datetime.now(timezone.utc)
    await _seed(db_session, test_user.id, now - timedelta(days=3), 1800)

    data = (await api_auth_client.get("/api/v1/focus/summary")).json()
    assert data["today_seconds"] == 0
    # week_seconds no se puede fijar: hace 3 dias cae dentro o fuera de la
    # semana segun el dia en que corra el test.


async def test_local_day_start_uses_the_client_offset_not_utc():
    """A las 01:00 UTC, en Buenos Aires (-180) todavia es el dia anterior.

    Sin el offset el corte de "hoy" caeria a las 21:00 hora local: una sesion de
    las 22:00 quedaria contada en el dia equivocado.
    """
    from app.modules.focus.service import _local_day_start_utc

    now_utc = datetime(2026, 9, 3, 1, 0, tzinfo=timezone.utc)  # 22:00 del 2 en AR

    assert _local_day_start_utc(now_utc, 0) == datetime(2026, 9, 3, 0, 0, tzinfo=timezone.utc)
    # Medianoche del 2 en Buenos Aires = 03:00 UTC del 2.
    assert _local_day_start_utc(now_utc, -180) == datetime(
        2026, 9, 2, 3, 0, tzinfo=timezone.utc
    )


async def test_summary_counts_a_session_by_the_users_local_day(
    api_auth_client, db_session, test_user
):
    """Una sesion de hace 30 min siempre es "hoy" para el reloj del usuario."""
    now = datetime.now(timezone.utc)
    await _seed(db_session, test_user.id, now - timedelta(minutes=30), 600)

    # -180 (Buenos Aires): la medianoche local siempre queda mas de 30 min atras
    # salvo en la franja 00:00-00:30 local, que este test no puede provocar.
    data = (
        await api_auth_client.get("/api/v1/focus/summary", params={"tz_offset_minutes": -180})
    ).json()
    local_now = now - timedelta(minutes=180)
    minutos_desde_medianoche = local_now.hour * 60 + local_now.minute
    if minutos_desde_medianoche >= 30:
        assert data["today_seconds"] == 600
    else:
        # Corriendo entre 00:00 y 00:30 hora local, la sesion es de ayer.
        assert data["today_seconds"] == 0


async def test_summary_rejects_an_absurd_timezone_offset(api_auth_client):
    resp = await api_auth_client.get(
        "/api/v1/focus/summary", params={"tz_offset_minutes": 5000}
    )
    assert resp.status_code == 422


# ── Historial ────────────────────────────────────────────────────────────────

async def test_sessions_are_listed_newest_first(api_auth_client, db_session, test_user):
    now = datetime.now(timezone.utc)
    await _seed(db_session, test_user.id, now - timedelta(hours=5), 600)
    await _seed(db_session, test_user.id, now - timedelta(hours=1), 900)

    sessions = (await api_auth_client.get("/api/v1/focus/sessions")).json()
    assert [s["duration_seconds"] for s in sessions] == [900, 600]


async def test_delete_removes_a_session(api_auth_client, db_session, test_user):
    session = await _seed(db_session, test_user.id, datetime.now(timezone.utc), 600)

    resp = await api_auth_client.delete(f"/api/v1/focus/sessions/{session.id}")
    assert resp.status_code == 204
    assert (await api_auth_client.get("/api/v1/focus/sessions")).json() == []


async def test_delete_of_an_unknown_session_is_404(api_auth_client):
    assert (await api_auth_client.delete("/api/v1/focus/sessions/nope")).status_code == 404


# ── Aislamiento entre usuarios ───────────────────────────────────────────────

async def test_sessions_of_another_user_are_not_visible(
    api_auth_client, db_session, test_user
):
    from app.core.security import hash_password
    from app.modules.auth.models import User

    otro = User(
        email="otro@test.com",
        password_hash=hash_password("test123"),
        full_name="Otro",
        is_active=True,
    )
    db_session.add(otro)
    await db_session.commit()

    ajena = await _seed(db_session, otro.id, datetime.now(timezone.utc), 1200)

    assert (await api_auth_client.get("/api/v1/focus/sessions")).json() == []
    assert (await api_auth_client.get("/api/v1/focus/summary")).json()["today_seconds"] == 0
    # Tampoco se puede borrar la sesion de otro.
    assert (await api_auth_client.delete(f"/api/v1/focus/sessions/{ajena.id}")).status_code == 404


async def test_stopping_does_not_touch_another_users_running_session(
    api_auth_client, db_session, test_user
):
    from app.core.security import hash_password
    from app.modules.auth.models import User

    otro = User(
        email="otro2@test.com",
        password_hash=hash_password("test123"),
        full_name="Otro",
        is_active=True,
    )
    db_session.add(otro)
    await db_session.commit()
    ajena = await _seed(db_session, otro.id, datetime.now(timezone.utc), None)

    # El usuario logueado no tiene sesion propia: no puede cerrar la del otro.
    assert (await api_auth_client.post("/api/v1/focus/stop")).status_code == 404

    activa_del_otro = await FocusService(db_session).get_active(otro.id)
    assert activa_del_otro is not None
    assert activa_del_otro.id == ajena.id

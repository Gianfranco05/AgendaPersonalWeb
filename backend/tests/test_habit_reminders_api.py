"""API de avisos de habitos: configuracion, vista del dia y campos por habito."""

from datetime import timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.main import app
from app.modules.habitos_recordatorios import api_routes
from app.modules.habitos_recordatorios.models import (
    HabitReminderDispatch,
    HabitReminderSettings,
)
from habit_reminder_helpers import TODAY, add_goal, add_record, add_token, utc

pytestmark = pytest.mark.asyncio

SETTINGS = "/api/v1/habit-reminders/settings"
TODAY_URL = "/api/v1/habit-reminders/today"
GOALS = "/api/v1/goals"


async def settings_rows(db_session) -> int:
    return (await db_session.execute(select(func.count()).select_from(HabitReminderSettings))).scalar()


@pytest.fixture
def clock(monkeypatch):
    """Fija el 'ahora' del endpoint /today (UTC)."""
    now = {"value": utc(25, 21)}  # 18:00 locales en UTC-3
    monkeypatch.setattr(api_routes, "utc_now", lambda: now["value"])
    return now


# ── GET / PUT settings ──────────────────────────────────────────────────────


async def test_las_rutas_exigen_sesion(client):
    assert (await client.get(SETTINGS)).status_code == 401
    assert (await client.put(SETTINGS, json={"enabled": False})).status_code == 401
    assert (await client.get(TODAY_URL)).status_code == 401


async def test_get_sin_fila_devuelve_los_defaults_encendidos_y_no_crea_fila(
    api_auth_client, db_session
):
    resp = await api_auth_client.get(SETTINGS)
    assert resp.status_code == 200
    assert resp.json() == {
        "enabled": True,
        "time": "20:00",
        "daily_cap": 3,
        "streak_alerts": True,
        "timezone_offset_minutes": None,
        "has_push_devices": False,
    }
    assert await settings_rows(db_session) == 0


async def test_has_push_devices_refleja_los_tokens(api_auth_client, db_session, test_user):
    await add_token(db_session, test_user.id)
    assert (await api_auth_client.get(SETTINGS)).json()["has_push_devices"] is True


async def test_put_guarda_y_devuelve_la_configuracion(api_auth_client, db_session):
    resp = await api_auth_client.put(
        SETTINGS, json={"enabled": True, "time": "21:15", "timezone_offset_minutes": -180}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["time"] == "21:15" and body["timezone_offset_minutes"] == -180
    assert (await api_auth_client.get(SETTINGS)).json()["time"] == "21:15"
    assert await settings_rows(db_session) == 1


async def test_apagar_con_un_toque(api_auth_client):
    resp = await api_auth_client.put(SETTINGS, json={"enabled": False})
    assert resp.json()["enabled"] is False
    assert (await api_auth_client.get(SETTINGS)).json()["enabled"] is False


async def test_put_parcial_conserva_el_resto(api_auth_client):
    await api_auth_client.put(
        SETTINGS, json={"time": "08:05", "daily_cap": 5, "timezone_offset_minutes": 60}
    )
    resp = await api_auth_client.put(SETTINGS, json={"streak_alerts": False})
    body = resp.json()
    assert body["streak_alerts"] is False
    assert (body["time"], body["daily_cap"], body["timezone_offset_minutes"]) == ("08:05", 5, 60)
    assert body["enabled"] is True


@pytest.mark.parametrize(
    "payload",
    [
        {"time": "24:00"},
        {"time": "7:30"},
        {"time": "12:60"},
        {"daily_cap": 0},
        {"daily_cap": 6},
        {"timezone_offset_minutes": 841},
        {"timezone_offset_minutes": -841},
    ],
)
async def test_put_rechaza_valores_invalidos_con_422(api_auth_client, db_session, payload):
    resp = await api_auth_client.put(SETTINGS, json=payload)
    assert resp.status_code == 422
    assert await settings_rows(db_session) == 0


async def test_put_acepta_los_limites(api_auth_client):
    for payload in ({"time": "00:00"}, {"time": "23:59"}, {"daily_cap": 1}, {"daily_cap": 5},
                    {"timezone_offset_minutes": 840}, {"timezone_offset_minutes": -840}):
        assert (await api_auth_client.put(SETTINGS, json=payload)).status_code == 200


async def test_null_explicito_en_campo_no_nulo_se_ignora_pero_el_offset_se_borra(api_auth_client):
    await api_auth_client.put(SETTINGS, json={"time": "09:00", "timezone_offset_minutes": 60})
    resp = await api_auth_client.put(
        SETTINGS, json={"enabled": None, "time": None, "daily_cap": None, "streak_alerts": None}
    )
    body = resp.json()
    assert (body["enabled"], body["time"], body["daily_cap"], body["streak_alerts"]) == (
        True, "09:00", 3, True,
    )
    cleared = await api_auth_client.put(SETTINGS, json={"timezone_offset_minutes": None})
    assert cleared.json()["timezone_offset_minutes"] is None


async def test_la_configuracion_es_por_usuario(api_auth_client, client, db_session):
    await api_auth_client.put(SETTINGS, json={"enabled": False, "time": "06:00"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as other:
        reg = await other.post("/auth/api/register", json={
            "email": "otro@test.com", "full_name": "Otro", "password": "testpass123",
            "accept_terms": True, "confirm_age": True,
        })
        assert reg.status_code == 201
        theirs = (await other.get(SETTINGS)).json()
        assert theirs["enabled"] is True and theirs["time"] == "20:00"
        await other.put(SETTINGS, json={"daily_cap": 5})
    mine = (await api_auth_client.get(SETTINGS)).json()
    assert (mine["enabled"], mine["time"], mine["daily_cap"]) == (False, "06:00", 3)


# ── /today ──────────────────────────────────────────────────────────────────


async def test_today_antes_de_la_hora_lista_los_pendientes_como_upcoming(
    api_auth_client, db_session, test_user, clock
):
    await add_goal(db_session, test_user.id, "Agua", icon="💧")
    await add_goal(db_session, test_user.id, "Leer")
    resp = await api_auth_client.get(TODAY_URL, params={"tz_offset_minutes": -180})
    body = resp.json()
    assert body["local_date"] == "2026-10-25" and body["enabled"] is True
    assert body["pending_count"] == 2
    assert [(s["time"], s["status"]) for s in body["slots"]] == [("20:00", "upcoming")]
    habits = body["slots"][0]["habits"]
    assert [(h["title"], h["icon"], h["streak"]) for h in habits] == [
        ("Agua", "💧", 0), ("Leer", "fa-bullseye", 0),
    ]
    assert set(habits[0]) == {"id", "title", "icon", "streak"}


async def test_today_muestra_el_estado_registrado_y_la_racha(
    api_auth_client, db_session, test_user, clock
):
    goal = await add_goal(db_session, test_user.id, "Leer")
    for back in range(1, 6):
        await add_record(db_session, test_user.id, goal.id, TODAY - timedelta(days=back))
    db_session.add(HabitReminderDispatch(
        user_id=test_user.id, local_date=TODAY, slot="20:00", status="sent"))
    await db_session.commit()
    clock["value"] = utc(26, 0)  # 21:00 locales
    body = (await api_auth_client.get(TODAY_URL, params={"tz_offset_minutes": -180})).json()
    assert body["slots"][0]["status"] == "sent"
    assert body["slots"][0]["habits"][0]["streak"] == 5


async def test_today_con_todo_marcado_tiene_pending_count_cero(
    api_auth_client, db_session, test_user, clock
):
    goal = await add_goal(db_session, test_user.id)
    await add_record(db_session, test_user.id, goal.id, TODAY)
    body = (await api_auth_client.get(TODAY_URL, params={"tz_offset_minutes": -180})).json()
    assert body["pending_count"] == 0 and body["slots"] == []


async def test_today_usa_el_offset_guardado_y_si_no_hay_argentina(
    api_auth_client, db_session, test_user, clock
):
    await add_goal(db_session, test_user.id)
    clock["value"] = utc(26, 1)  # 22:00 del 25 en UTC-3, ya 02:00 del 26 en UTC+1
    assert (await api_auth_client.get(TODAY_URL)).json()["local_date"] == "2026-10-25"
    await api_auth_client.put(SETTINGS, json={"timezone_offset_minutes": 60})
    assert (await api_auth_client.get(TODAY_URL)).json()["local_date"] == "2026-10-26"
    # El parametro pisa lo guardado.
    forced = await api_auth_client.get(TODAY_URL, params={"tz_offset_minutes": -180})
    assert forced.json()["local_date"] == "2026-10-25"


async def test_today_rechaza_un_offset_fuera_de_rango(api_auth_client, clock):
    assert (await api_auth_client.get(TODAY_URL, params={"tz_offset_minutes": 900})).status_code == 422


async def test_today_no_muestra_habitos_de_otro_usuario(api_auth_client, db_session, clock):
    from habit_reminder_helpers import add_user

    other = await add_user(db_session, "usuario-dos")
    await add_goal(db_session, other.id, "Ajeno")
    body = (await api_auth_client.get(TODAY_URL, params={"tz_offset_minutes": -180})).json()
    assert body["pending_count"] == 0


# ── Campos por habito en /goals ─────────────────────────────────────────────


async def create_goal(client, **extra):
    resp = await client.post(GOALS, json={"title": "Leer", "goal_type": "binary", **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_crear_habito_con_hora_propia(api_auth_client):
    goal = await create_goal(api_auth_client, reminder_time="07:30")
    assert goal["reminder_enabled"] is True and goal["reminder_time"] == "07:30"
    listed = (await api_auth_client.get(GOALS)).json()[0]
    assert (listed["reminder_enabled"], listed["reminder_time"]) == (True, "07:30")


async def test_cliente_viejo_sin_campos_nuevos_obtiene_los_defaults(api_auth_client):
    goal = await create_goal(api_auth_client)
    assert goal["reminder_enabled"] is True and goal["reminder_time"] is None


async def test_editar_hora_borrarla_y_excluir(api_auth_client):
    goal = await create_goal(api_auth_client, reminder_time="07:30")
    url = f"{GOALS}/{goal['id']}"
    edited = (await api_auth_client.put(url, json={"reminder_time": "22:05"})).json()
    assert edited["reminder_time"] == "22:05"
    # Otro campo no toca la hora propia.
    assert (await api_auth_client.put(url, json={"title": "Leer mas"})).json()["reminder_time"] == "22:05"
    cleared = (await api_auth_client.put(url, json={"reminder_time": None})).json()
    assert cleared["reminder_time"] is None
    excluded = (await api_auth_client.put(url, json={"reminder_enabled": False})).json()
    assert excluded["reminder_enabled"] is False
    # Un null explicito en un campo no nulo se ignora.
    kept = (await api_auth_client.put(url, json={"reminder_enabled": None})).json()
    assert kept["reminder_enabled"] is False


async def test_hora_propia_invalida_es_422_en_crear_y_editar(api_auth_client):
    bad = await api_auth_client.post(GOALS, json={"title": "X", "reminder_time": "25:00"})
    assert bad.status_code == 422
    goal = await create_goal(api_auth_client)
    bad = await api_auth_client.put(f"{GOALS}/{goal['id']}", json={"reminder_time": "9:00"})
    assert bad.status_code == 422


async def test_checkin_devuelve_tambien_los_campos_de_aviso(api_auth_client):
    goal = await create_goal(api_auth_client, reminder_time="07:30", reminder_enabled=False)
    resp = await api_auth_client.put(
        f"{GOALS}/{goal['id']}/checkin", json={"record_date": "2026-10-25", "value": 1}
    )
    assert (resp.json()["reminder_enabled"], resp.json()["reminder_time"]) == (False, "07:30")


async def test_editar_el_habito_de_otro_usuario_es_404_y_no_cambia(
    api_auth_client, db_session
):
    from habit_reminder_helpers import add_user

    other = await add_user(db_session, "usuario-dos")
    theirs = await add_goal(db_session, other.id, "Ajeno", reminder_hour=9, reminder_minute=0)
    resp = await api_auth_client.put(
        f"{GOALS}/{theirs.id}", json={"reminder_enabled": False, "reminder_time": "10:00"}
    )
    assert resp.status_code == 404
    await db_session.refresh(theirs)
    assert (theirs.reminder_enabled, theirs.reminder_hour) == (True, 9)

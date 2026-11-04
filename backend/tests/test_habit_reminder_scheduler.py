"""Scheduler de avisos de habitos: husos, agrupacion, tope, ventana y dedup."""

import asyncio
import json
from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.base import Base
from app.modules.habitos_recordatorios import scheduler
from app.modules.habitos_recordatorios.models import HabitReminderDispatch
from app.modules.push.service import PushService
from habit_reminder_helpers import (
    TODAY,
    add_goal,
    add_record,
    add_token,
    add_user,
    set_config,
    utc,
)

pytestmark = pytest.mark.asyncio

# 2026-10-25, UTC-3: 20:00 locales = 23:00 UTC.
DAY = 25


@pytest.fixture(autouse=True)
def _clean_state():
    scheduler._handled.clear()
    scheduler._last_prune = None
    yield
    scheduler._handled.clear()


@pytest_asyncio.fixture
async def pushes(engine, monkeypatch):
    """Apunta el scheduler a la base de test y captura las push (nunca llama a Expo)."""
    monkeypatch.setattr(
        scheduler,
        "AsyncSessionLocal",
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
    )
    sent: list[dict] = []

    async def fake_send(self, user_id, title, body, data=None):
        sent.append({"user_id": user_id, "title": title, "body": body, "data": data})

    monkeypatch.setattr(PushService, "send_to_user", fake_send)
    return sent


@pytest_asyncio.fixture
async def user(db_session, test_user):
    await add_token(db_session, test_user.id)
    return test_user


async def rows(db_session, user_id=None):
    db_session.expire_all()
    query = select(HabitReminderDispatch).order_by(
        HabitReminderDispatch.local_date, HabitReminderDispatch.slot
    )
    if user_id:
        query = query.where(HabitReminderDispatch.user_id == user_id)
    return [(r.slot, r.status) for r in (await db_session.execute(query)).scalars().all()]


# ── Encendido por defecto ───────────────────────────────────────────────────


async def test_usuario_con_token_y_sin_fila_recibe_a_las_20_locales(pushes, db_session, user):
    goal = await add_goal(db_session, user.id, "Tomar agua")
    await scheduler._tick(utc(DAY, 23))

    assert len(pushes) == 1
    push = pushes[0]
    assert push["user_id"] == user.id
    assert push["title"] == "✅ Can_cen"
    assert push["body"] == "Todavía no marcaste «Tomar agua» hoy."
    assert push["data"] == {
        "type": "habit_reminder",
        "local_date": "2026-10-25",
        "goal_ids": [goal.id],
    }
    assert await rows(db_session) == [("20:00", "sent")]


async def test_usuario_sin_token_no_recibe_nada_ni_deja_filas(pushes, db_session, test_user):
    await add_goal(db_session, test_user.id)
    await scheduler._tick(utc(DAY, 23))
    assert pushes == []
    assert await rows(db_session) == []


async def test_interruptor_apagado_no_envia(pushes, db_session, user):
    await add_goal(db_session, user.id)
    await set_config(db_session, user.id, enabled=False)
    await scheduler._tick(utc(DAY, 23))
    assert pushes == [] and await rows(db_session) == []


async def test_usuario_sin_dispositivos_al_enviar_queda_no_devices(
    pushes, db_session, user, monkeypatch
):
    await add_goal(db_session, user.id)

    async def no_tokens(self, user_id):
        return []

    monkeypatch.setattr(PushService, "tokens_for_user", no_tokens)
    await scheduler._tick(utc(DAY, 23))
    assert pushes == []
    assert await rows(db_session) == [("20:00", "no_devices")]


# ── Husos horarios ──────────────────────────────────────────────────────────


async def test_offset_nulo_usa_argentina_y_no_dispara_a_las_20_utc(pushes, db_session, user):
    await add_goal(db_session, user.id)
    await set_config(db_session, user.id, timezone_offset_minutes=None)
    await scheduler._tick(utc(DAY, 20))  # 17:00 locales
    assert pushes == []
    await scheduler._tick(utc(DAY, 23))
    assert len(pushes) == 1


async def test_offset_positivo_dispara_a_las_19_utc(pushes, db_session, user):
    await add_goal(db_session, user.id)
    await set_config(db_session, user.id, timezone_offset_minutes=60)
    await scheduler._tick(utc(DAY, 18, 59))
    assert pushes == []
    await scheduler._tick(utc(DAY, 19))
    assert len(pushes) == 1


async def test_registro_en_la_fecha_local_cerca_de_medianoche_utc(pushes, db_session, user):
    goal = await add_goal(db_session, user.id, reminder_hour=22, reminder_minute=30)
    await add_record(db_session, user.id, goal.id, date(2026, 10, 25))
    # 01:30 UTC del 26 = 22:30 del 25 en UTC-3: ya esta marcado en ese dia local.
    await scheduler._tick(utc(26, 1, 30))
    assert pushes == []
    assert await rows(db_session) == [("22:30", "nothing")]


async def test_marcado_el_dia_anterior_no_cuenta_para_hoy(pushes, db_session, user):
    goal = await add_goal(db_session, user.id)
    await add_record(db_session, user.id, goal.id, date(2026, 10, 24))
    await scheduler._tick(utc(DAY, 23))
    assert len(pushes) == 1


# ── Agrupacion, horas propias y tope ────────────────────────────────────────


async def test_tres_pendientes_a_la_misma_hora_son_una_sola_push(pushes, db_session, user):
    for name in ("Agua", "Leer", "Correr"):
        await add_goal(db_session, user.id, name)
    await scheduler._tick(utc(DAY, 23))
    assert len(pushes) == 1
    assert pushes[0]["title"] == "✅ Te faltan 3 hábitos hoy"
    assert pushes[0]["body"] == "Agua, Leer y Correr"


async def test_los_ya_marcados_no_entran_en_la_push(pushes, db_session, user):
    agua = await add_goal(db_session, user.id, "Agua")
    await add_goal(db_session, user.id, "Leer")
    await add_record(db_session, user.id, agua.id, TODAY)
    await scheduler._tick(utc(DAY, 23))
    assert pushes[0]["body"] == "Todavía no marcaste «Leer» hoy."


async def test_todo_marcado_no_envia_y_queda_nothing(pushes, db_session, user):
    goal = await add_goal(db_session, user.id)
    await add_record(db_session, user.id, goal.id, TODAY)
    await scheduler._tick(utc(DAY, 23))
    assert pushes == []
    assert await rows(db_session) == [("20:00", "nothing")]


async def test_hora_propia_solo_se_evalua_en_su_slot(pushes, db_session, user):
    await add_goal(db_session, user.id, "Agua")
    await add_goal(db_session, user.id, "Leer", reminder_hour=22, reminder_minute=30)
    await scheduler._tick(utc(DAY, 23))  # 20:00
    assert [p["body"] for p in pushes] == ["Todavía no marcaste «Agua» hoy."]
    await scheduler._tick(utc(26, 1, 30))  # 22:30
    assert [p["body"] for p in pushes][1] == "Todavía no marcaste «Leer» hoy."
    assert len(pushes) == 2


async def test_tope_diario_de_dos_corta_el_tercer_slot(pushes, db_session, user):
    await set_config(db_session, user.id, daily_cap=2)
    await add_goal(db_session, user.id, "A", reminder_hour=8, reminder_minute=0)
    await add_goal(db_session, user.id, "B", reminder_hour=13, reminder_minute=0)
    await add_goal(db_session, user.id, "C")
    await scheduler._tick(utc(DAY, 11))  # 08:00
    await scheduler._tick(utc(DAY, 16))  # 13:00
    await scheduler._tick(utc(DAY, 23))  # 20:00
    assert len(pushes) == 2
    assert await rows(db_session) == [("08:00", "sent"), ("13:00", "sent"), ("20:00", "capped")]


async def test_la_racha_cambia_el_texto_pero_no_suma_pushes(pushes, db_session, user):
    goal = await add_goal(db_session, user.id, "Leer")
    for back in range(1, 13):
        await add_record(db_session, user.id, goal.id, TODAY - timedelta(days=back))
    await scheduler._tick(utc(DAY, 23))
    assert len(pushes) == 1
    assert pushes[0]["body"] == "🔥 Llevás 12 días seguidos con «Leer». ¡No la cortes hoy!"


async def test_racha_corta_o_alertas_apagadas_texto_plano(pushes, db_session, user):
    goal = await add_goal(db_session, user.id, "Leer")
    for back in (1, 2):
        await add_record(db_session, user.id, goal.id, TODAY - timedelta(days=back))
    await scheduler._tick(utc(DAY, 23))
    assert pushes[0]["body"] == "Todavía no marcaste «Leer» hoy."


async def test_alertas_de_racha_apagadas_en_la_configuracion(pushes, db_session, user):
    await set_config(db_session, user.id, streak_alerts=False)
    goal = await add_goal(db_session, user.id, "Leer")
    for back in range(1, 8):
        await add_record(db_session, user.id, goal.id, TODAY - timedelta(days=back))
    await scheduler._tick(utc(DAY, 23))
    assert pushes[0]["body"] == "Todavía no marcaste «Leer» hoy."


# ── Ventana de recuperacion ─────────────────────────────────────────────────


async def test_antes_de_la_hora_no_evalua(pushes, db_session, user):
    await add_goal(db_session, user.id)
    await scheduler._tick(utc(DAY, 22, 59))  # 19:59 locales
    assert pushes == [] and await rows(db_session) == []


async def test_volver_a_las_20_40_envia_y_a_las_21_05_no(pushes, db_session, user):
    await add_goal(db_session, user.id)
    await scheduler._tick(utc(DAY, 23, 40))
    assert len(pushes) == 1


async def test_volver_pasada_la_ventana_no_envia(pushes, db_session, user):
    await add_goal(db_session, user.id)
    await scheduler._tick(utc(26, 0, 5))  # 21:05 locales
    assert pushes == [] and await rows(db_session) == []


async def test_slot_de_las_23_30_no_se_recupera_al_dia_siguiente(pushes, db_session, user):
    await add_goal(db_session, user.id, reminder_hour=23, reminder_minute=30)
    await scheduler._tick(utc(26, 3, 10))  # 00:10 del 26 local
    assert pushes == [] and await rows(db_session) == []


async def test_dos_slots_tras_una_caida_se_fusionan_en_una_push(pushes, db_session, user):
    await add_goal(db_session, user.id, "Agua")
    await add_goal(db_session, user.id, "Leer", reminder_hour=20, reminder_minute=15)
    await scheduler._tick(utc(DAY, 23, 20))  # el server vuelve a las 20:20
    assert len(pushes) == 1
    assert pushes[0]["title"] == "✅ Te faltan 2 hábitos hoy"
    assert pushes[0]["body"] == "Agua y Leer"
    assert await rows(db_session) == [("20:00", "sent"), ("20:15", "merged")]


# ── Dedup ───────────────────────────────────────────────────────────────────


async def test_ciclos_cada_minuto_de_20_00_a_20_59_envian_una(pushes, db_session, user):
    await add_goal(db_session, user.id)
    for minute in range(60):
        await scheduler._tick(utc(DAY, 23, minute))
    assert len(pushes) == 1


async def test_reinicio_sin_redis_no_reenvia_por_la_fila_unica(pushes, db_session, user):
    await add_goal(db_session, user.id)
    await scheduler._tick(utc(DAY, 23))
    scheduler._handled.clear()  # el proceso se reinicia: pierde la memoria
    await scheduler._tick(utc(DAY, 23, 5))
    assert len(pushes) == 1
    assert await rows(db_session) == [("20:00", "sent")]


async def test_claim_de_redis_perdido_no_envia(pushes, db_session, user, monkeypatch):
    await add_goal(db_session, user.id)

    async def lost(key, ttl):
        return False

    monkeypatch.setattr(scheduler, "claim_once", lost)
    await scheduler._tick(utc(DAY, 23))
    assert pushes == [] and await rows(db_session) == []


async def test_la_clave_de_redis_incluye_usuario_fecha_y_slot(pushes, db_session, user, monkeypatch):
    await add_goal(db_session, user.id)
    keys = []

    async def spy(key, ttl):
        keys.append((key, ttl))
        return True

    monkeypatch.setattr(scheduler, "claim_once", spy)
    await scheduler._tick(utc(DAY, 23))
    assert keys == [(f"habit-reminder:{user.id}:2026-10-25:20:00", 129600)]


async def test_error_de_base_al_marcar_no_envia_y_el_ciclo_siguiente_reintenta(
    pushes, db_session, user, monkeypatch
):
    await add_goal(db_session, user.id)
    released = []

    async def release(key):
        released.append(key)

    monkeypatch.setattr(scheduler, "release_claim", release)
    real = scheduler._insert_dispatches
    calls = {"n": 0}

    async def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("base caida un instante")
        return await real(*args, **kwargs)

    monkeypatch.setattr(scheduler, "_insert_dispatches", flaky)

    await scheduler._tick(utc(DAY, 23))  # falla: no hay push, se libera el claim
    assert pushes == [] and len(released) == 1
    await scheduler._tick(utc(DAY, 23, 1))  # reintenta dentro de la ventana
    assert len(pushes) == 1
    assert await rows(db_session) == [("20:00", "sent")]


async def test_expo_caido_no_corta_el_ciclo_de_los_demas(pushes, db_session, user, monkeypatch):
    from habit_reminder_helpers import add_user

    other = await add_user(db_session, "usuario-dos")
    await add_token(db_session, other.id)
    await add_goal(db_session, user.id, "Agua")
    await add_goal(db_session, other.id, "Leer")
    sent = []

    async def flaky_send(self, user_id, title, body, data=None):
        if user_id == user.id:
            raise RuntimeError("expo caido")
        sent.append((user_id, body))

    monkeypatch.setattr(PushService, "send_to_user", flaky_send)
    await scheduler._tick(utc(DAY, 23))
    assert sent == [(other.id, "Todavía no marcaste «Leer» hoy.")]


async def test_dos_usuarios_no_se_mezclan(pushes, db_session, user):
    from habit_reminder_helpers import add_user

    other = await add_user(db_session, "usuario-dos")
    await add_token(db_session, other.id)
    mine = await add_goal(db_session, user.id, "Agua")
    theirs = await add_goal(db_session, other.id, "Leer")
    await add_record(db_session, other.id, mine.id, TODAY)  # registro ajeno sobre MI habito
    await scheduler._tick(utc(DAY, 23))

    by_user = {p["user_id"]: p for p in pushes}
    assert by_user[user.id]["data"]["goal_ids"] == [mine.id]
    assert by_user[other.id]["data"]["goal_ids"] == [theirs.id]
    assert by_user[user.id]["body"] == "Todavía no marcaste «Agua» hoy."


async def test_dos_workers_concurrentes_envian_una_sola_push(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'workers.db'}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(scheduler, "AsyncSessionLocal", factory)
    sent = []

    async def fake_send(self, user_id, title, body, data=None):
        sent.append(title)

    monkeypatch.setattr(PushService, "send_to_user", fake_send)

    async with factory() as db:
        await add_user(db, "u1")
        await add_token(db, "u1")
        await add_goal(db, "u1", "Agua")

    async def tick():
        try:
            await scheduler._tick(utc(DAY, 23))
        except Exception:  # "database is locked" del otro worker: el resultado no cambia
            pass

    # Cada "worker" tiene su propia memoria: se simula vaciandola entre ciclos.
    async def worker():
        await tick()

    await asyncio.gather(worker(), worker(), worker())
    scheduler._handled.clear()
    await tick()

    async with factory() as db:
        count = (await db.execute(select(func.count()).select_from(HabitReminderDispatch))).scalar()
    assert len(sent) == 1 and count == 1
    await engine.dispose()


# ── Retencion ───────────────────────────────────────────────────────────────


async def test_poda_las_filas_de_mas_de_30_dias(pushes, db_session, user):
    old = HabitReminderDispatch(
        user_id=user.id, local_date=TODAY - timedelta(days=31), slot="20:00", status="sent"
    )
    recent = HabitReminderDispatch(
        user_id=user.id, local_date=TODAY - timedelta(days=29), slot="20:00", status="sent"
    )
    db_session.add_all([old, recent])
    await db_session.commit()
    await scheduler._tick(utc(DAY, 12))
    remaining = [r.local_date for r in (await db_session.execute(select(HabitReminderDispatch))).scalars()]
    assert remaining == [TODAY - timedelta(days=29)]


async def test_los_goal_ids_se_guardan_sin_titulos(pushes, db_session, user):
    goal_id = (await add_goal(db_session, user.id, "Terapia privada")).id
    await scheduler._tick(utc(DAY, 23))
    db_session.expire_all()
    row = (await db_session.execute(select(HabitReminderDispatch))).scalar_one()
    assert json.loads(row.goal_ids) == [goal_id]
    assert "Terapia" not in (row.goal_ids or "")

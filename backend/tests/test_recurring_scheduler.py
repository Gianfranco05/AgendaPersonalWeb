"""Scheduler de recurrentes: ventana horaria local, husos, recuperacion tras una
caida, idempotencia (workers concurrentes, ciclos repetidos, fallos a mitad) y
push agrupadas."""

import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.base import Base
from app.modules.auth.models import User
from app.modules.finanzas.models import Transaction
from app.modules.push.service import PushService
from app.modules.recurrentes import rules, scheduler
from app.modules.recurrentes.models import RecurringOccurrence, RecurringTransaction
from app.modules.recurrentes.service import RecurringService

pytestmark = pytest.mark.asyncio

BASE = "/api/v1/finance/recurring"
TX = "/api/v1/finance/transactions"


def utc(month: int, day: int, hour: int, minute: int = 0, year: int = 2026) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


@pytest.fixture
def clock(monkeypatch):
    """Reloj de la API: alta de las plantillas el 2026-10-25 a las 12:00 locales."""
    state = {"now": utc(10, 25, 15)}
    monkeypatch.setattr(rules, "utc_now", lambda: state["now"])
    return state


@pytest_asyncio.fixture
async def pushes(engine, monkeypatch):
    """Apunta el scheduler a la base de test y captura las push enviadas."""
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


def body(**overrides):
    values = {
        "type": "income",
        "name": "Sueldo",
        "amount": "850000",
        "frequency": "monthly",
        "day_of_month": 5,
        "start_date": "2026-11-01",
        "timezone_offset_minutes": -180,
    }
    values.update(overrides)
    return values


async def create(client, **overrides):
    resp = await client.post(BASE, json=body(**overrides))
    assert resp.status_code == 201, resp.text
    return resp.json()


async def dates_of(client):
    resp = await client.get(TX, params={"limit": 200})
    return sorted(t["transaction_date"] for t in resp.json()["items"])


# ── Ventana horaria y husos ──────────────────────────────────────────────────


async def test_a_las_9_locales_genera_el_sueldo(api_auth_client, clock, pushes):
    rec = await create(api_auth_client)
    await scheduler._tick(utc(11, 5, 12))  # 09:00 en UTC-3
    assert await dates_of(api_auth_client) == ["2026-11-05"]
    got = (await api_auth_client.get(f"{BASE}/{rec['id']}")).json()
    assert got["next_occurrence_date"] == "2026-12-05"
    tx = (await api_auth_client.get(TX)).json()["items"][0]
    assert tx["recurrence_id"] == rec["id"] and tx["is_recurring"] is True


async def test_a_las_8_59_locales_todavia_no(api_auth_client, clock, pushes):
    await create(api_auth_client)
    await scheduler._tick(utc(11, 5, 11, 59))
    assert await dates_of(api_auth_client) == []
    await scheduler._tick(utc(11, 5, 12, 0))
    assert await dates_of(api_auth_client) == ["2026-11-05"]


async def test_fuera_de_la_ventana_de_la_noche_no_genera(api_auth_client, clock, pushes):
    await create(api_auth_client)
    # 22:00 locales (01:00 UTC del 6): fuera de la ventana; el 21:59 si entra.
    await scheduler._tick(utc(11, 6, 1, 0))
    assert await dates_of(api_auth_client) == []
    await scheduler._tick(utc(11, 6, 0, 59))
    assert await dates_of(api_auth_client) == ["2026-11-05"]


async def test_fecha_local_distinta_de_la_utc(api_auth_client, clock, pushes):
    await create(api_auth_client)
    # Primer ciclo tras una caida: 2026-11-06 01:30 UTC = 2026-11-05 22:30 local (fuera de ventana).
    await scheduler._tick(utc(11, 6, 1, 30))
    assert await dates_of(api_auth_client) == []
    await scheduler._tick(utc(11, 6, 12, 0))
    assert await dates_of(api_auth_client) == ["2026-11-05"]


async def test_offset_positivo(api_auth_client, clock, pushes):
    await create(api_auth_client, timezone_offset_minutes=600)
    # 2026-11-04 23:00 UTC = 2026-11-05 09:00 locales (+10).
    await scheduler._tick(utc(11, 4, 22, 59))
    assert await dates_of(api_auth_client) == []
    await scheduler._tick(utc(11, 4, 23, 0))
    assert await dates_of(api_auth_client) == ["2026-11-05"]


async def test_sin_offset_usa_el_de_argentina(api_auth_client, clock, pushes):
    await create(api_auth_client, timezone_offset_minutes=None)
    await scheduler._tick(utc(11, 5, 11, 59))
    assert await dates_of(api_auth_client) == []
    await scheduler._tick(utc(11, 5, 12, 0))
    assert await dates_of(api_auth_client) == ["2026-11-05"]


async def test_plantilla_pausada_o_terminada_no_genera(api_auth_client, clock, pushes):
    pausada = await create(api_auth_client, name="Pausada")
    await create(api_auth_client, name="Terminada", start_date="2026-10-26", end_date="2026-10-30")
    await api_auth_client.post(f"{BASE}/{pausada['id']}/pause", json={})
    await scheduler._tick(utc(11, 5, 12))
    await scheduler._tick(utc(12, 5, 12))
    assert await dates_of(api_auth_client) == []
    assert pushes == []


async def test_lo_que_cae_durante_la_pausa_no_se_genera(api_auth_client, clock, pushes):
    rec = await create(api_auth_client)
    await api_auth_client.post(f"{BASE}/{rec['id']}/pause", json={})
    clock["now"] = utc(12, 10, 15)
    await api_auth_client.post(f"{BASE}/{rec['id']}/resume", json={})
    await scheduler._tick(utc(12, 10, 15))
    await scheduler._tick(utc(1, 5, 12, year=2027))
    assert await dates_of(api_auth_client) == ["2027-01-05"]


# ── Recuperacion tras una caida ──────────────────────────────────────────────


async def test_caida_de_3_dias_genera_4_con_sus_fechas_originales(api_auth_client, clock, pushes):
    await create(api_auth_client, frequency="daily", day_of_month=None, start_date="2026-10-25")
    assert await dates_of(api_auth_client) == ["2026-10-25"]
    await scheduler._tick(utc(10, 29, 12))
    assert await dates_of(api_auth_client) == [
        "2026-10-25",
        "2026-10-26",
        "2026-10-27",
        "2026-10-28",
        "2026-10-29",
    ]


async def test_caida_mas_larga_que_el_tope_genera_solo_los_ultimos_62_dias(
    api_auth_client, clock, pushes, db_session
):
    rec = await create(api_auth_client, frequency="daily", day_of_month=None, start_date="2026-10-25")
    # 2027-01-30: cursor 2026-10-26 => 96 fechas vencidas.
    await scheduler._tick(utc(1, 30, 12, year=2027))
    dates = await dates_of(api_auth_client)
    assert len(dates) == 1 + 62
    assert dates[1] == "2026-11-30"  # 62 dias contando el 30/01
    assert dates[-1] == "2027-01-30"
    got = (await api_auth_client.get(f"{BASE}/{rec['id']}")).json()
    assert got["next_occurrence_date"] == "2027-01-31"


# ── Idempotencia ─────────────────────────────────────────────────────────────


async def test_ciclos_repetidos_dejan_una_sola_transaccion(api_auth_client, clock, pushes):
    await create(api_auth_client)
    for minute in range(0, 6):
        await scheduler._tick(utc(11, 5, 12, minute))
    await scheduler._tick(utc(11, 5, 20, 30))
    assert await dates_of(api_auth_client) == ["2026-11-05"]
    assert len(pushes) == 1


async def test_reinicio_sin_redis_no_regenera(api_auth_client, clock, pushes, monkeypatch):
    # No hay estado en proceso ni Redis: lo que decide es la base.
    import app.core.redis_claim as redis_claim

    async def boom(*args, **kwargs):  # pragma: no cover - no deberia llamarse
        raise AssertionError("las recurrentes no usan Redis")

    monkeypatch.setattr(redis_claim, "claim_once", boom)
    await create(api_auth_client)
    await scheduler._tick(utc(11, 5, 12))
    # "Reinicio": el scheduler no guarda nada en memoria, el segundo ciclo parte de cero.
    await scheduler._tick(utc(11, 5, 13))
    assert await dates_of(api_auth_client) == ["2026-11-05"]


async def test_fallo_a_mitad_revierte_todo_y_el_ciclo_siguiente_reintenta(
    api_auth_client, clock, pushes, monkeypatch
):
    rec = await create(api_auth_client, frequency="daily", day_of_month=None, start_date="2026-10-25")
    original = RecurringService._build_transaction
    calls = {"n": 0}

    async def flaky(self, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("falla simulada en la 2.ª transacción")
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(RecurringService, "_build_transaction", flaky)
    await scheduler._tick(utc(10, 28, 12))  # 26, 27 y 28 vencidas
    assert await dates_of(api_auth_client) == ["2026-10-25"]
    got = (await api_auth_client.get(f"{BASE}/{rec['id']}")).json()
    assert got["next_occurrence_date"] == "2026-10-26"
    assert pushes == []

    monkeypatch.setattr(RecurringService, "_build_transaction", original)
    await scheduler._tick(utc(10, 28, 12, 1))
    assert await dates_of(api_auth_client) == ["2026-10-25", "2026-10-26", "2026-10-27", "2026-10-28"]


async def test_una_plantilla_rota_no_frena_a_las_demas(api_auth_client, clock, pushes, monkeypatch):
    await create(api_auth_client, name="Rota")
    await create(api_auth_client, name="Sana")
    original = RecurringService._build_transaction

    async def selective(self, rec, *args, **kwargs):
        if rec.name == "Rota":
            raise RuntimeError("rota")
        return await original(self, rec, *args, **kwargs)

    monkeypatch.setattr(RecurringService, "_build_transaction", selective)
    await scheduler._tick(utc(11, 5, 12))
    items = (await api_auth_client.get(TX)).json()["items"]
    assert [t["product_name"] for t in items] == ["Sana"]


async def test_dos_workers_concurrentes_generan_una_sola_transaccion(tmp_path, monkeypatch):
    """Dos ciclos a la vez sobre la misma plantilla, con conexiones distintas."""
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
        db.add(User(id="u1", email="w@test.com", password_hash="x", full_name="W", is_active=True, is_verified=True))
        await db.commit()
        db.add(
            RecurringTransaction(
                id="r1",
                user_id="u1",
                type="income",
                name="Sueldo",
                amount=Decimal("850000"),
                currency="ARS",
                frequency="monthly",
                interval_count=1,
                day_of_month=5,
                start_date=date(2026, 11, 5),
                anchor_date=date(2026, 11, 5),
                next_occurrence_date=date(2026, 11, 5),
                status="active",
                timezone_offset_minutes=-180,
            )
        )
        await db.commit()

    async def tick():
        try:
            await scheduler._tick(utc(11, 5, 12))
        except Exception:  # un "database is locked" del segundo worker no cambia el resultado
            pass

    await asyncio.gather(tick(), tick(), tick())
    await tick()

    async with factory() as db:
        count = (await db.execute(select(func.count()).select_from(Transaction))).scalar()
        occ = (await db.execute(select(func.count()).select_from(RecurringOccurrence))).scalar()
        rec = (await db.execute(select(RecurringTransaction))).scalar_one()
    assert count == 1 and occ == 1
    assert rec.next_occurrence_date == date(2026, 12, 5)
    assert sent == ["Se registró: Sueldo"]
    await engine.dispose()


# ── Push ─────────────────────────────────────────────────────────────────────


async def test_push_de_un_movimiento_registrado(api_auth_client, clock, pushes):
    rec = await create(api_auth_client)
    await scheduler._tick(utc(11, 5, 12))
    assert len(pushes) == 1
    push = pushes[0]
    assert push["title"] == "Se registró: Sueldo"
    assert "Ingreso de $ 850.000,00 ARS" in push["body"]
    tx = (await api_auth_client.get(TX)).json()["items"][0]
    assert push["data"] == {
        "type": "recurring_generated",
        "recurrence_id": rec["id"],
        "transaction_id": tx["id"],
    }


async def test_push_de_un_gasto_menciona_la_cuenta(api_auth_client, clock, pushes):
    acc = (
        await api_auth_client.post(
            "/api/v1/finance/accounts",
            json={"name": "Cuenta", "bank_name": "Banco Galicia", "account_type": "checking"},
        )
    ).json()["id"]
    await create(api_auth_client, type="expense", name="Alquiler", amount="300000", bank_account_id=acc)
    await scheduler._tick(utc(11, 5, 12))
    assert pushes[0]["body"] == "Gasto de $ 300.000,00 ARS en Banco Galicia."


async def test_push_de_un_pendiente(api_auth_client, clock, pushes):
    rec = await create(
        api_auth_client, name="Luz", type="expense", amount="25000", requires_confirmation=True
    )
    await scheduler._tick(utc(11, 5, 12))
    assert len(pushes) == 1
    occ = (await api_auth_client.get(f"{BASE}/occurrences")).json()[0]
    assert pushes[0]["title"] == "Confirmá el monto: Luz"
    assert "$ 25.000,00 ARS" in pushes[0]["body"]
    assert pushes[0]["data"] == {
        "type": "recurring_confirm",
        "occurrence_id": occ["id"],
        "recurrence_id": rec["id"],
    }
    assert await dates_of(api_auth_client) == []


async def test_push_de_pendiente_sin_estimado_invita_a_cargar_el_monto(api_auth_client, clock, pushes):
    payload = body(name="Luz", type="expense", requires_confirmation=True)
    del payload["amount"]
    assert (await api_auth_client.post(BASE, json=payload)).status_code == 201
    await scheduler._tick(utc(11, 5, 12))
    assert pushes[0]["body"] == "Tocá para cargar el monto."


async def test_resumen_agrupado_por_usuario_y_ciclo(api_auth_client, clock, pushes):
    await create(api_auth_client, frequency="daily", day_of_month=None, start_date="2026-10-26", name="Diario")
    await create(
        api_auth_client,
        name="Luz",
        type="expense",
        requires_confirmation=True,
        frequency="daily",
        day_of_month=None,
        start_date="2026-10-28",
    )
    await scheduler._tick(utc(10, 28, 12))
    # Diario: 26, 27, 28 (3 movimientos); Luz: 28 (1 pendiente) -> un solo push.
    assert len(pushes) == 1
    assert pushes[0]["title"] == "Movimientos recurrentes"
    assert pushes[0]["body"] == "Se registraron 3 movimientos y tenés 1 para confirmar."
    assert pushes[0]["data"] == {"type": "recurring_summary"}


async def test_resumen_solo_con_pendientes(api_auth_client, clock, pushes):
    await create(
        api_auth_client, name="Luz", requires_confirmation=True, frequency="daily",
        day_of_month=None, start_date="2026-10-26",
    )
    await scheduler._tick(utc(10, 27, 12))
    assert pushes[0]["body"] == "Tenés 2 movimientos para confirmar."


async def test_sin_aviso_no_hay_push_pero_si_transaccion(api_auth_client, clock, pushes):
    await create(api_auth_client, notify=False)
    await scheduler._tick(utc(11, 5, 12))
    assert pushes == []
    assert await dates_of(api_auth_client) == ["2026-11-05"]


async def test_generar_desde_la_api_no_manda_push(api_auth_client, clock, pushes):
    await create(api_auth_client, start_date="2026-10-25", day_of_month=25)
    assert await dates_of(api_auth_client) == ["2026-10-25"]
    assert pushes == []


async def test_expo_caido_no_afecta_lo_generado(api_auth_client, clock, engine, monkeypatch):
    monkeypatch.setattr(
        scheduler,
        "AsyncSessionLocal",
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
    )

    async def broken(self, *args, **kwargs):
        raise RuntimeError("Expo caido")

    monkeypatch.setattr(PushService, "send_to_user", broken)
    await create(api_auth_client)
    await create(api_auth_client, name="Otro")
    await scheduler._tick(utc(11, 5, 12))
    assert await dates_of(api_auth_client) == ["2026-11-05", "2026-11-05"]


async def test_usuario_sin_tokens_genera_sin_error(api_auth_client, clock, engine, monkeypatch):
    monkeypatch.setattr(
        scheduler,
        "AsyncSessionLocal",
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
    )
    await create(api_auth_client)
    await scheduler._tick(utc(11, 5, 12))  # PushService real: sin tokens, vuelve sin red
    assert await dates_of(api_auth_client) == ["2026-11-05"]

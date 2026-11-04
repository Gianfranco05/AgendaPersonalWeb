"""Avisos push de vencimiento: ventana horaria, husos y dedup en tres capas."""

import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.inversiones import scheduler
from app.modules.inversiones.models import Investment
from app.modules.inversiones.repository import InvestmentRepository
from app.modules.inversiones.valuation import fixed_term_info
from app.modules.push.service import PushService

pytestmark = pytest.mark.asyncio

MATURITY = date(2026, 10, 20)


def utc(day: int, hour: int, minute: int = 0, month: int = 10) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _clean_state():
    scheduler._handled.clear()
    yield
    scheduler._handled.clear()


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


async def add_investment(db_session, user, **overrides) -> Investment:
    values = dict(
        user_id=user.id,
        asset_type="fixed_term",
        name="Plazo fijo Galicia",
        currency="ARS",
        invested_amount=Decimal("1000000"),
        interest_rate_tna=Decimal("30"),
        start_date=date(2026, 10, 1),
        maturity_date=MATURITY,
        status="active",
        notify_maturity=True,
        timezone_offset_minutes=-180,
    )
    values.update(overrides)
    inv = Investment(**values)
    db_session.add(inv)
    await db_session.commit()
    return inv


# ── Cuando toca avisar ──────────────────────────────────────────────────────


async def test_aviso_de_vispera_a_las_9_locales(pushes, db_session, test_user):
    inv = await add_investment(db_session, test_user)
    # 12:00 UTC = 09:00 en UTC-3, el dia anterior al vencimiento.
    await scheduler._tick(utc(19, 12))

    assert len(pushes) == 1
    push = pushes[0]
    assert push["title"] == "Vence mañana: Plazo fijo Galicia"
    assert push["user_id"] == test_user.id
    assert push["data"] == {"type": "investment_maturity", "investment_id": inv.id}
    amount = fixed_term_info(
        Decimal("1000000"), Decimal("30"), date(2026, 10, 1), MATURITY, date(2026, 10, 19)
    ).amount_at_maturity
    assert amount == Decimal("1015616.44")
    assert push["body"] == "Tu plazo fijo cobra $ 1.015.616,44 ARS."


async def test_aviso_del_dia_del_vencimiento(pushes, db_session, test_user):
    await add_investment(db_session, test_user, institution="Banco Galicia")
    await scheduler._tick(utc(20, 12))
    assert [p["title"] for p in pushes] == ["Vence hoy: Plazo fijo Galicia"]
    assert pushes[0]["body"] == "Tu plazo fijo en Banco Galicia cobra $ 1.015.616,44 ARS."


async def test_los_otros_tipos_avisan_sin_monto(pushes, db_session, test_user):
    await add_investment(
        db_session, test_user, asset_type="bond", name="Bono AL30", interest_rate_tna=None, start_date=None
    )
    await scheduler._tick(utc(20, 12))
    assert pushes[0]["title"] == "Vence hoy: Bono AL30"
    assert pushes[0]["body"] == "Bono AL30 vence hoy."


async def test_en_dolares_el_monto_sale_en_dolares(pushes, db_session, test_user):
    await add_investment(
        db_session, test_user, currency="USD", invested_amount=Decimal("1000"), interest_rate_tna=Decimal("3")
    )
    await scheduler._tick(utc(20, 12))
    assert "US$" in pushes[0]["body"] and pushes[0]["body"].endswith("USD.")


async def test_no_avisa_antes_de_las_9_locales(pushes, db_session, test_user):
    await add_investment(db_session, test_user)
    await scheduler._tick(utc(19, 11, 59))  # 08:59 locales
    assert pushes == []
    await scheduler._tick(utc(19, 12, 0))
    assert len(pushes) == 1


async def test_recupera_el_aviso_si_el_server_estuvo_caido_a_las_9(pushes, db_session, test_user):
    await add_investment(db_session, test_user)
    await scheduler._tick(utc(20, 14, 30))  # 11:30 locales, primer ciclo del dia
    assert [p["title"] for p in pushes] == ["Vence hoy: Plazo fijo Galicia"]


async def test_no_avisa_desde_las_22_locales(pushes, db_session, test_user):
    await add_investment(db_session, test_user)
    await scheduler._tick(utc(21, 0, 59))  # 21:59 locales del dia 20: aun en ventana
    assert len(pushes) == 1
    scheduler._handled.clear()

    # Otro activo: primer ciclo del dia a las 22:00 locales.
    await add_investment(db_session, test_user, name="Tarde", maturity_date=date(2026, 10, 25))
    await scheduler._tick(utc(26, 1, 0))  # 22:00 locales del dia 25
    assert [p["title"] for p in pushes if p["title"].endswith("Tarde")] == []


async def test_dias_que_no_son_vispera_ni_vencimiento_no_avisan(pushes, db_session, test_user):
    await add_investment(db_session, test_user)
    for day in (17, 18, 21, 22):
        await scheduler._tick(utc(day, 12))
    assert pushes == []


@pytest.mark.parametrize(
    "overrides",
    [{"notify_maturity": False}, {"status": "closed"}, {"maturity_date": None}],
    ids=["sin-aviso", "cerrado", "sin-vencimiento"],
)
async def test_no_avisa_si_esta_apagado_cerrado_o_sin_vencimiento(
    pushes, db_session, test_user, overrides
):
    await add_investment(db_session, test_user, **overrides)
    for day in (19, 20):
        await scheduler._tick(utc(day, 12))
    assert pushes == []


# ── Huso horario ────────────────────────────────────────────────────────────


async def test_sin_offset_usa_argentina(pushes, db_session, test_user):
    await add_investment(db_session, test_user, timezone_offset_minutes=None)
    await scheduler._tick(utc(19, 11, 59))
    assert pushes == []
    await scheduler._tick(utc(19, 12, 0))
    assert len(pushes) == 1


async def test_offset_positivo(pushes, db_session, test_user):
    await add_investment(db_session, test_user, timezone_offset_minutes=60)
    # 09:00 de UTC+1 son las 08:00 UTC.
    await scheduler._tick(utc(19, 7, 59))
    assert pushes == []
    await scheduler._tick(utc(19, 8, 0))
    assert len(pushes) == 1


async def test_el_dia_local_puede_ser_distinto_al_de_utc(pushes, db_session, test_user):
    # UTC+14 (Kiribati): las 09:00 locales del dia 19 son las 19:00 UTC del 18.
    await add_investment(db_session, test_user, timezone_offset_minutes=840)
    await scheduler._tick(utc(18, 19, 0))
    assert [p["title"] for p in pushes] == ["Vence mañana: Plazo fijo Galicia"]


# ── Resiliencia ─────────────────────────────────────────────────────────────


async def test_usuario_sin_tokens_no_rompe(engine, db_session, test_user, monkeypatch):
    monkeypatch.setattr(
        scheduler,
        "AsyncSessionLocal",
        async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
    )
    inv_id = (await add_investment(db_session, test_user)).id
    await scheduler._tick(utc(19, 12))  # PushService real, sin tokens registrados

    db_session.expire_all()
    row = (await db_session.execute(select(Investment).where(Investment.id == inv_id))).scalar_one()
    assert row.eve_notice_for == MATURITY


async def test_expo_caido_en_un_activo_no_corta_a_los_demas(
    pushes, db_session, test_user, monkeypatch
):
    await add_investment(db_session, test_user, name="Roto")
    await add_investment(db_session, test_user, name="Sano")

    async def flaky_send(self, user_id, title, body, data=None):
        if "Roto" in title:
            raise RuntimeError("Expo caido")
        pushes.append({"title": title})

    monkeypatch.setattr(PushService, "send_to_user", flaky_send)
    await scheduler._tick(utc(19, 12))  # no levanta
    assert [p["title"] for p in pushes] == ["Vence mañana: Sano"]


async def test_un_ciclo_con_error_de_db_no_mata_el_loop(monkeypatch):
    calls = {"n": 0}

    async def failing_tick():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("db caida")
        raise asyncio.CancelledError

    async def no_sleep(_):
        return None

    monkeypatch.setattr(scheduler, "_tick", failing_tick)
    monkeypatch.setattr(scheduler.asyncio, "sleep", no_sleep)
    with pytest.raises(asyncio.CancelledError):
        await scheduler.run_investment_alert_scheduler()
    assert calls["n"] == 2  # el primer fallo se logueo y el loop siguio


# ── Dedup en tres capas ─────────────────────────────────────────────────────


async def test_ciclos_repetidos_en_la_ventana_mandan_un_solo_aviso(pushes, db_session, test_user):
    await add_investment(db_session, test_user)
    minute = utc(20, 12)  # 09:00 locales del dia del vencimiento
    while minute < utc(21, 1):  # hasta las 21:59 locales
        await scheduler._tick(minute)
        minute += timedelta(minutes=7)
    assert len(pushes) == 1


async def test_dos_ciclos_concurrentes_mandan_una_sola_push(pushes, db_session, test_user):
    await add_investment(db_session, test_user)
    await asyncio.gather(scheduler._tick(utc(19, 12)), scheduler._tick(utc(19, 12)))
    assert len(pushes) == 1


async def test_dos_workers_se_reparten_el_aviso_por_la_marca_persistente(
    engine, db_session, test_user
):
    inv = await add_investment(db_session, test_user)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s1, maker() as s2:
        first = await InvestmentRepository(s1).claim_notice(inv.id, "eve", MATURITY)
        second = await InvestmentRepository(s2).claim_notice(inv.id, "eve", MATURITY)
    assert (first, second) == (True, False)
    # El aviso "hoy" tiene su propia marca.
    async with maker() as s3:
        assert await InvestmentRepository(s3).claim_notice(inv.id, "day", MATURITY) is True


async def test_reinicio_sin_redis_no_reenvia(pushes, db_session, test_user):
    await add_investment(db_session, test_user)
    await scheduler._tick(utc(19, 12))
    assert len(pushes) == 1

    scheduler._handled.clear()  # el proceso se reinicia: se pierde la memoria
    await scheduler._tick(utc(19, 13))
    assert len(pushes) == 1


async def test_claim_de_redis_perdido_no_envia(pushes, db_session, test_user, monkeypatch):
    inv_id = (await add_investment(db_session, test_user)).id

    async def lost(key, ttl):
        return False

    monkeypatch.setattr(scheduler, "claim_once", lost)
    await scheduler._tick(utc(19, 12))
    assert pushes == []
    # El otro worker es quien manda: este no toca la marca persistente.
    db_session.expire_all()
    row = (await db_session.execute(select(Investment).where(Investment.id == inv_id))).scalar_one()
    assert row.eve_notice_for is None


async def test_la_clave_de_redis_incluye_activo_tipo_y_vencimiento(
    pushes, db_session, test_user, monkeypatch
):
    inv = await add_investment(db_session, test_user)
    claimed: list[tuple[str, int]] = []

    async def spy(key, ttl):
        claimed.append((key, ttl))
        return True

    monkeypatch.setattr(scheduler, "claim_once", spy)
    await scheduler._tick(utc(19, 12))
    assert claimed == [(f"investment-maturity:{inv.id}:eve:2026-10-20", 129600)]


async def test_redis_caido_no_pierde_el_aviso(pushes, db_session, test_user, monkeypatch):
    from app.config import settings
    from app.core import redis_claim

    class BrokenRedis:
        async def set(self, *a, **k):
            raise ConnectionError("redis caido")

    await add_investment(db_session, test_user)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://fake")
    monkeypatch.setattr(redis_claim, "_redis_client", BrokenRedis())
    await scheduler._tick(utc(19, 12))
    assert len(pushes) == 1


async def test_vispera_y_vencimiento_son_dos_avisos_distintos(pushes, db_session, test_user):
    await add_investment(db_session, test_user)
    await scheduler._tick(utc(19, 12))
    await scheduler._tick(utc(20, 12))
    assert [p["title"].split(":")[0] for p in pushes] == ["Vence mañana", "Vence hoy"]


async def test_cambiar_el_vencimiento_rehabilita_los_avisos(pushes, db_session, test_user):
    inv = await add_investment(db_session, test_user)
    await scheduler._tick(utc(19, 12))
    await scheduler._tick(utc(20, 12))
    assert len(pushes) == 2

    inv.maturity_date = date(2026, 10, 25)
    await db_session.commit()
    await scheduler._tick(utc(24, 12))
    await scheduler._tick(utc(25, 12))
    assert [p["title"].split(":")[0] for p in pushes] == [
        "Vence mañana",
        "Vence hoy",
        "Vence mañana",
        "Vence hoy",
    ]


async def test_se_poda_la_memoria_de_avisos_viejos(pushes, db_session, test_user):
    await add_investment(db_session, test_user)
    await scheduler._tick(utc(19, 12))
    assert len(scheduler._handled) == 1
    await scheduler._tick(utc(30, 12))  # vencimiento viejo: sale de la memoria
    assert scheduler._handled == set()

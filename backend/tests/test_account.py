from datetime import date

import pytest
from sqlalchemy import func, select

from app.core.base import Base
from app.core.security import hash_password
from app.modules.anotaciones.models import Note, Tag, note_tags
from app.modules.auth.models import User
from app.modules.billing.models import StripeCustomer
from app.modules.modulos.models import ModulePurchase
from app.modules.cuenta.service import OWNED_TABLES, RETAINED_TABLES
from app.modules.fitness.models import Exercise, WorkoutSession
from app.modules.finanzas.models import Category, Transaction
from app.modules.inversiones.models import Investment
from app.modules.recurrentes.models import RecurringOccurrence, RecurringTransaction
from app.modules.metas.models import Goal, HabitRecord
from app.modules.tareas.models import Task

# La contrasena del usuario de la fixture `test_user` (ver conftest.py).
TEST_PASSWORD = "test123"


def test_owned_tables_cubre_todos_los_modelos_con_user_id():
    """Un modelo nuevo con user_id tiene que sumarse a OWNED_TABLES.

    Si no, queda fuera del export (el usuario se lleva un volcado incompleto) y
    fuera del borrado (quedan filas huerfanas apuntando a un usuario que ya no
    existe). Este test es el que hace que la lista no se pudra.
    """
    registradas = {nombre for nombre, _ in [*OWNED_TABLES, *RETAINED_TABLES]}
    con_user_id = {
        tabla.name
        for tabla in Base.metadata.tables.values()
        if "user_id" in tabla.columns
    }
    faltantes = con_user_id - registradas
    assert not faltantes, (
        f"Tablas con user_id que faltan en OWNED_TABLES: {sorted(faltantes)}. "
        "Agregalas respetando el orden de borrado (hijos antes que padres)."
    )


def test_tablas_de_mercado_son_globales_y_no_se_exportan_ni_borran():
    """Cotizaciones, IPC y precios no pertenecen a un usuario: sin `user_id`, y
    por eso fuera de OWNED_TABLES. Las preferencias nuevas salen en el export
    porque viajan con `user_preferences`."""
    mercado = {"fx_quotes", "inflation_monthly", "market_prices", "market_fetch_state"}
    for nombre in mercado:
        assert "user_id" not in Base.metadata.tables[nombre].columns
    registradas = {nombre for nombre, _ in [*OWNED_TABLES, *RETAINED_TABLES]}
    assert not (mercado & registradas)
    columnas = Base.metadata.tables["user_preferences"].columns
    assert "fx_usd_source" in columnas and "fx_eur_source" in columnas


async def _seed_datos(db_session, user):
    """Crea al menos una fila en las tablas con relaciones no triviales."""
    categoria = Category(user_id=str(user.id), name="Comida")
    db_session.add(categoria)
    await db_session.flush()

    db_session.add(
        Transaction(
            user_id=str(user.id),
            product_name="Almuerzo",
            amount=1500.50,
            type="expense",
            transaction_date="2026-08-07",
            category_id=categoria.id,
        )
    )

    meta = Goal(user_id=str(user.id), title="Correr", goal_type="binary")
    db_session.add(meta)
    await db_session.flush()
    db_session.add(
        HabitRecord(
            user_id=str(user.id), goal_id=meta.id, record_date=date(2026, 8, 7), value=1
        )
    )

    sesion = WorkoutSession(
        user_id=str(user.id), title="Pierna", session_date=date(2026, 8, 7)
    )
    db_session.add(sesion)
    await db_session.flush()
    db_session.add(Exercise(session_id=sesion.id, name="Sentadilla", sets=4, reps=8))

    nota = Note(user_id=str(user.id), title="Idea", content="algo")
    etiqueta = Tag(user_id=str(user.id), name="personal")
    db_session.add_all([nota, etiqueta])
    await db_session.flush()
    # Insert directo en la tabla de asociacion: `nota.tags.append(...)` dispara
    # un lazy-load sincrono de la coleccion, que en sesion async explota con
    # MissingGreenlet.
    await db_session.execute(
        note_tags.insert().values(note_id=nota.id, tag_id=etiqueta.id)
    )

    db_session.add(Task(user_id=str(user.id), title="Comprar pan"))
    plazo = Investment(
        user_id=str(user.id),
        asset_type="fixed_term",
        name="Plazo fijo",
        currency="ARS",
        invested_amount=1000000,
        interest_rate_tna=30,
        start_date=date(2026, 10, 1),
        maturity_date=date(2026, 10, 31),
    )
    db_session.add(plazo)
    await db_session.flush()
    # Cadena de renovacion: el borrado tiene que sacar a las dos (FK a si misma).
    db_session.add(
        Investment(
            user_id=str(user.id),
            asset_type="fixed_term",
            name="Plazo fijo (renovado)",
            currency="ARS",
            status="closed",
            invested_amount=1024657.53,
            interest_rate_tna=28,
            start_date=date(2026, 10, 31),
            maturity_date=date(2026, 11, 30),
            renewed_from_id=plazo.id,
        )
    )
    recurrente = RecurringTransaction(
        user_id=str(user.id),
        type="expense",
        name="Luz",
        amount=25000,
        category_id=categoria.id,
        frequency="monthly",
        day_of_month=10,
        start_date=date(2026, 8, 1),
        anchor_date=date(2026, 8, 10),
        next_occurrence_date=date(2026, 9, 10),
        requires_confirmation=True,
    )
    db_session.add(recurrente)
    await db_session.flush()
    generada = Transaction(
        user_id=str(user.id),
        product_name="Luz",
        amount=25000,
        type="expense",
        transaction_date="2026-08-10",
        is_recurring=True,
        recurring_parent_id=recurrente.id,
    )
    db_session.add(generada)
    await db_session.flush()
    db_session.add_all(
        [
            RecurringOccurrence(
                user_id=str(user.id),
                recurrence_id=recurrente.id,
                occurrence_date=date(2026, 8, 10),
                status="confirmed",
                transaction_id=generada.id,
            ),
            RecurringOccurrence(
                user_id=str(user.id),
                recurrence_id=recurrente.id,
                occurrence_date=date(2026, 9, 10),
                status="pending",
                suggested_amount=25000,
            ),
        ]
    )
    db_session.add(StripeCustomer(user_id=str(user.id), stripe_customer_id="cus_test"))
    db_session.add(ModulePurchase(user_id=str(user.id), module_key="study", amount_paid=1500))

    await db_session.commit()


@pytest.mark.asyncio
async def test_export_incluye_los_datos_del_usuario(
    api_auth_client, db_session, test_user
):
    await _seed_datos(db_session, test_user)

    response = await api_auth_client.get("/api/v1/me/export")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]

    data = response.json()
    assert data["user"]["email"] == test_user.email
    assert len(data["transactions"]) == 2
    assert {t["product_name"] for t in data["transactions"]} == {"Almuerzo", "Luz"}
    assert len(data["recurring_transactions"]) == 1
    assert data["recurring_transactions"][0]["name"] == "Luz"
    assert data["recurring_transactions"][0]["next_occurrence_date"] == "2026-09-10"
    assert len(data["recurring_occurrences"]) == 2
    # Numeric(12,2) sale como Decimal en Postgres: el export tiene que
    # entregarlo como numero JSON, no romper al serializar.
    assert data["transactions"][0]["amount"] == pytest.approx(1500.50)
    assert len(data["habit_records"]) == 1
    assert len(data["tasks"]) == 1
    # Date y Numeric salen como JSON valido (no son serializables a secas).
    assert len(data["investments"]) == 2
    plazo = next(i for i in data["investments"] if i["name"] == "Plazo fijo")
    assert plazo["maturity_date"] == "2026-10-31"
    assert plazo["invested_amount"] == pytest.approx(1000000)
    renovado = next(i for i in data["investments"] if i["name"] == "Plazo fijo (renovado)")
    assert renovado["renewed_from_id"] == plazo["id"]
    # Exercise no tiene user_id: se escopa por las sesiones del usuario.
    assert len(data["exercises"]) == 1
    assert data["exercises"][0]["name"] == "Sentadilla"
    # note_tags no tiene modelo propio; sin el, se pierde que etiqueta tenia la nota.
    assert len(data["note_tags"]) == 1


@pytest.mark.asyncio
async def test_export_incluye_age_confirmed_at(api_auth_client, db_session, test_user):
    from datetime import datetime, timezone

    test_user.age_confirmed_at = datetime(2026, 10, 26, 15, 30, tzinfo=timezone.utc)
    await db_session.commit()

    response = await api_auth_client.get("/api/v1/me/export")
    assert response.status_code == 200
    assert response.json()["user"]["age_confirmed_at"].startswith("2026-10-26")


@pytest.mark.asyncio
async def test_export_no_incluye_credenciales(api_auth_client, db_session, test_user):
    await _seed_datos(db_session, test_user)

    response = await api_auth_client.get("/api/v1/me/export")
    data = response.json()

    assert "password_hash" not in data["user"]
    assert "refresh_tokens" not in data
    assert "verification_tokens" not in data
    # Identificadores internos de Stripe: no son datos del usuario y exponerlos
    # solo sirve para enumerar la cuenta de Stripe del negocio.
    assert "stripe_customer_id" not in data["stripe_customers"][0]
    assert "stripe_session_id" not in data["module_purchases"][0]
    # Lo que si le sirve al usuario: que compro y cuanto pago.
    assert data["module_purchases"][0]["module_key"] == "study"
    assert data["module_purchases"][0]["amount_paid"] == 1500


@pytest.mark.asyncio
async def test_export_no_filtra_datos_de_otro_usuario(
    api_auth_client, db_session, test_user
):
    await _seed_datos(db_session, test_user)

    otro = User(
        email="otro@example.com",
        password_hash=hash_password("otra-password"),
        full_name="Otro",
    )
    db_session.add(otro)
    await db_session.flush()
    db_session.add(Task(user_id=str(otro.id), title="Tarea ajena"))
    await db_session.commit()

    response = await api_auth_client.get("/api/v1/me/export")
    titulos = [t["title"] for t in response.json()["tasks"]]
    assert "Tarea ajena" not in titulos


@pytest.mark.asyncio
async def test_export_no_incluye_inversiones_de_otro_usuario(
    api_auth_client, db_session, test_user
):
    otro = User(
        email="inversor@example.com",
        password_hash=hash_password("otra-password"),
        full_name="Inversor",
    )
    db_session.add(otro)
    await db_session.flush()
    db_session.add(
        Investment(
            user_id=str(otro.id),
            asset_type="stock",
            name="Accion ajena",
            currency="ARS",
            invested_amount=10,
        )
    )
    await db_session.commit()

    response = await api_auth_client.get("/api/v1/me/export")
    assert response.json()["investments"] == []


@pytest.mark.asyncio
async def test_export_no_incluye_recurrentes_de_otro_usuario(
    api_auth_client, db_session, test_user
):
    otro = User(
        email="recurrente@example.com",
        password_hash=hash_password("otra-password"),
        full_name="Otro",
    )
    db_session.add(otro)
    await db_session.flush()
    rec = RecurringTransaction(
        user_id=str(otro.id),
        type="income",
        name="Sueldo ajeno",
        amount=100,
        frequency="monthly",
        day_of_month=5,
        start_date=date(2026, 11, 1),
        anchor_date=date(2026, 11, 5),
        next_occurrence_date=date(2026, 11, 5),
    )
    db_session.add(rec)
    await db_session.flush()
    db_session.add(
        RecurringOccurrence(
            user_id=str(otro.id),
            recurrence_id=rec.id,
            occurrence_date=date(2026, 11, 5),
            status="pending",
        )
    )
    await db_session.commit()

    data = (await api_auth_client.get("/api/v1/me/export")).json()
    assert data["recurring_transactions"] == []
    assert data["recurring_occurrences"] == []


@pytest.mark.asyncio
async def test_export_requiere_autenticacion(client):
    response = await client.get("/api/v1/me/export")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_borra_la_cuenta_y_todos_sus_datos(
    api_auth_client, db_session, test_user
):
    await _seed_datos(db_session, test_user)
    user_id = str(test_user.id)

    response = await api_auth_client.request(
        "DELETE", "/api/v1/me", json={"password": TEST_PASSWORD}
    )
    assert response.status_code == 200

    db_session.expire_all()
    for nombre, modelo in OWNED_TABLES:
        total = await db_session.scalar(
            select(func.count()).select_from(modelo).where(modelo.user_id == user_id)
        )
        assert total == 0, f"quedaron filas en {nombre} tras borrar la cuenta"

    # Tablas sin user_id: se limpian por la tabla padre, no por columna propia.
    assert await db_session.scalar(select(func.count()).select_from(Exercise)) == 0
    assert await db_session.scalar(select(func.count()).select_from(note_tags)) == 0
    assert await db_session.scalar(
        select(func.count()).select_from(User).where(User.id == user_id)
    ) == 0


@pytest.mark.asyncio
async def test_delete_rechaza_password_incorrecta(
    api_auth_client, db_session, test_user
):
    user_id = str(test_user.id)

    response = await api_auth_client.request(
        "DELETE", "/api/v1/me", json={"password": "no-es-la-password"}
    )
    assert response.status_code == 403

    db_session.expire_all()
    assert await db_session.scalar(
        select(func.count()).select_from(User).where(User.id == user_id)
    ) == 1


@pytest.mark.asyncio
async def test_delete_no_toca_datos_de_otro_usuario(
    api_auth_client, db_session, test_user
):
    otro = User(
        email="sobreviviente@example.com",
        password_hash=hash_password("otra-password"),
        full_name="Sobreviviente",
    )
    db_session.add(otro)
    await db_session.flush()
    db_session.add(Task(user_id=str(otro.id), title="Sigue viva"))
    await db_session.commit()
    otro_id = str(otro.id)

    response = await api_auth_client.request(
        "DELETE", "/api/v1/me", json={"password": TEST_PASSWORD}
    )
    assert response.status_code == 200

    db_session.expire_all()
    assert await db_session.scalar(
        select(func.count()).select_from(User).where(User.id == otro_id)
    ) == 1
    assert await db_session.scalar(
        select(func.count()).select_from(Task).where(Task.user_id == otro_id)
    ) == 1


@pytest.mark.asyncio
async def test_delete_requiere_autenticacion(client):
    response = await client.request(
        "DELETE", "/api/v1/me", json={"password": TEST_PASSWORD}
    )
    assert response.status_code == 401


async def _seed_avisos_de_habitos(db_session, user_id: str, slot: str = "20:00"):
    from app.modules.habitos_recordatorios.models import (
        HabitReminderDispatch,
        HabitReminderSettings,
    )

    db_session.add(HabitReminderSettings(user_id=user_id, hour=21, minute=15, daily_cap=2))
    db_session.add(
        HabitReminderDispatch(
            user_id=user_id, local_date=date(2026, 10, 25), slot=slot, status="sent"
        )
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_export_incluye_los_avisos_de_habitos_propios_y_no_los_ajenos(
    api_auth_client, db_session, test_user
):
    otro = User(
        email="avisos-ajenos@example.com",
        password_hash=hash_password("otra-password"),
        full_name="Ajeno",
    )
    db_session.add(otro)
    await db_session.flush()
    await _seed_avisos_de_habitos(db_session, str(test_user.id), "20:00")
    await _seed_avisos_de_habitos(db_session, str(otro.id), "07:00")

    data = (await api_auth_client.get("/api/v1/me/export")).json()
    assert [(s["hour"], s["minute"], s["daily_cap"]) for s in data["habit_reminder_settings"]] == [
        (21, 15, 2)
    ]
    assert [d["slot"] for d in data["habit_reminder_dispatches"]] == ["20:00"]
    assert data["habit_reminder_dispatches"][0]["local_date"] == "2026-10-25"


@pytest.mark.asyncio
async def test_borrar_la_cuenta_borra_los_avisos_de_habitos_y_no_los_ajenos(
    api_auth_client, db_session, test_user
):
    from app.modules.habitos_recordatorios.models import (
        HabitReminderDispatch,
        HabitReminderSettings,
    )

    otro = User(
        email="avisos-sobreviviente@example.com",
        password_hash=hash_password("otra-password"),
        full_name="Sobreviviente",
    )
    db_session.add(otro)
    await db_session.flush()
    otro_id = str(otro.id)
    await _seed_avisos_de_habitos(db_session, str(test_user.id))
    await _seed_avisos_de_habitos(db_session, otro_id)

    response = await api_auth_client.request(
        "DELETE", "/api/v1/me", json={"password": TEST_PASSWORD}
    )
    assert response.status_code == 200

    db_session.expire_all()
    for model in (HabitReminderSettings, HabitReminderDispatch):
        rows = (await db_session.execute(select(model.user_id))).scalars().all()
        assert rows == [otro_id]

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
    assert len(data["transactions"]) == 1
    assert data["transactions"][0]["product_name"] == "Almuerzo"
    # Numeric(12,2) sale como Decimal en Postgres: el export tiene que
    # entregarlo como numero JSON, no romper al serializar.
    assert data["transactions"][0]["amount"] == pytest.approx(1500.50)
    assert len(data["habit_records"]) == 1
    assert len(data["tasks"]) == 1
    # Exercise no tiene user_id: se escopa por las sesiones del usuario.
    assert len(data["exercises"]) == 1
    assert data["exercises"][0]["name"] == "Sentadilla"
    # note_tags no tiene modelo propio; sin el, se pierde que etiqueta tenia la nota.
    assert len(data["note_tags"]) == 1


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

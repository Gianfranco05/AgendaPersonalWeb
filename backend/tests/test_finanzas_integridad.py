"""Integridad de categorias y fechas de transacciones.

Varios de estos casos solo fallaban en Postgres (SQLite no aplica FKs ni es
estricto con los tipos), asi que los tests verifican el comportamiento que no
depende del motor: el estado resultante y los 404.
"""

from datetime import date, datetime, time

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.modules.auth.models import User
from app.modules.finanzas.models import Budget, Category, IsoText, Transaction

TX = {
    "amount": "10.50",
    "type": "expense",
    "transaction_date": "2026-01-05",
    "account_type": "cash",
    "payment_method": "cash",
    "product_name": "Cafe",
}


def test_iso_text_convierte_fechas_y_horas_a_texto():
    t = IsoText(10)
    assert t.process_bind_param(date(2026, 1, 5), None) == "2026-01-05"
    assert t.process_bind_param(datetime(2026, 1, 5, 10, 30), None) == "2026-01-05"
    # Con microsegundos isoformat() mide 15 caracteres y no entra en String(10).
    assert t.process_bind_param(time(10, 30, 15, 123456), None) == "10:30:15"
    assert t.process_bind_param("2026-01-05", None) == "2026-01-05"
    assert t.process_bind_param(None, None) is None


@pytest.mark.asyncio
async def test_transaccion_guarda_fecha_y_hora_como_texto(api_auth_client, db_session):
    resp = await api_auth_client.post(
        "/api/v1/finance/transactions", json={**TX, "transaction_time": "10:30:15.250000"}
    )
    assert resp.status_code == 201
    tx = (await db_session.execute(select(Transaction))).scalar_one()
    assert tx.transaction_date == "2026-01-05"
    assert tx.transaction_time == "10:30:15"


@pytest.mark.asyncio
async def test_transaccion_con_categoria_ajena_da_404(api_auth_client, db_session):
    otro = User(email="otro@test.com", password_hash=hash_password("x12345"), full_name="Otro")
    db_session.add(otro)
    await db_session.commit()
    cat_ajena = Category(user_id=otro.id, name="Secreta")
    db_session.add(cat_ajena)
    await db_session.commit()

    resp = await api_auth_client.post(
        "/api/v1/finance/transactions", json={**TX, "category_id": cat_ajena.id}
    )
    assert resp.status_code == 404
    assert (await db_session.execute(select(Transaction))).first() is None


@pytest.mark.asyncio
async def test_transaccion_con_categoria_inexistente_da_404(api_auth_client):
    resp = await api_auth_client.post(
        "/api/v1/finance/transactions",
        json={**TX, "category_id": "11111111-1111-1111-1111-111111111111"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_actualizar_transaccion_con_categoria_ajena_da_404(
    api_auth_client, db_session, test_category
):
    otro = User(email="otro@test.com", password_hash=hash_password("x12345"), full_name="Otro")
    db_session.add(otro)
    await db_session.commit()
    cat_ajena = Category(user_id=otro.id, name="Secreta")
    db_session.add(cat_ajena)
    await db_session.commit()

    created = await api_auth_client.post(
        "/api/v1/finance/transactions", json={**TX, "category_id": test_category.id}
    )
    tx_id = created.json()["id"]
    resp = await api_auth_client.put(
        f"/api/v1/finance/transactions/{tx_id}", json={"category_id": cat_ajena.id}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_presupuesto_con_categoria_ajena_da_404(api_auth_client, db_session):
    otro = User(email="otro@test.com", password_hash=hash_password("x12345"), full_name="Otro")
    db_session.add(otro)
    await db_session.commit()
    cat_ajena = Category(user_id=otro.id, name="Secreta")
    db_session.add(cat_ajena)
    await db_session.commit()

    resp = await api_auth_client.post(
        "/api/v1/finance/budgets", json={"category_id": cat_ajena.id, "amount": "100"}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_borrar_categoria_desvincula_transacciones_presupuestos_y_hijas(
    api_auth_client, db_session, test_user, test_category
):
    hija = Category(user_id=test_user.id, name="Hija", parent_id=test_category.id)
    db_session.add(hija)
    await db_session.commit()
    created = await api_auth_client.post(
        "/api/v1/finance/transactions", json={**TX, "category_id": test_category.id}
    )
    assert created.status_code == 201
    budget = await api_auth_client.post(
        "/api/v1/finance/budgets", json={"category_id": test_category.id, "amount": "100"}
    )
    assert budget.status_code == 201

    resp = await api_auth_client.delete(f"/api/v1/finance/categories/{test_category.id}")
    assert resp.status_code == 204

    # La transaccion se conserva, sin categoria.
    tx = (await db_session.execute(select(Transaction))).scalar_one()
    await db_session.refresh(tx)
    assert tx.category_id is None
    assert (await db_session.execute(select(Budget))).first() is None
    await db_session.refresh(hija)
    assert hija.parent_id is None


@pytest.mark.asyncio
async def test_montos_fuera_de_rango_de_numeric_dan_422(api_auth_client, test_category):
    # Numeric(12, 2) admite hasta 9.999.999.999,99: mas daba 500 en Postgres.
    too_big = "99999999999"
    assert (await api_auth_client.post(
        "/api/v1/finance/transactions", json={**TX, "amount": too_big}
    )).status_code == 422
    assert (await api_auth_client.post(
        "/api/v1/finance/transactions", json={**TX, "unit_price": too_big}
    )).status_code == 422
    assert (await api_auth_client.post(
        "/api/v1/finance/transactions", json={**TX, "quantity": 3_000_000_000}
    )).status_code == 422
    assert (await api_auth_client.post(
        "/api/v1/finance/accounts",
        json={"name": "x", "account_type": "cash", "balance": too_big},
    )).status_code == 422
    assert (await api_auth_client.post(
        "/api/v1/finance/budgets", json={"category_id": test_category.id, "amount": too_big}
    )).status_code == 422

    ok = await api_auth_client.post(
        "/api/v1/finance/transactions", json={**TX, "amount": "9999999999.99"}
    )
    assert ok.status_code == 201

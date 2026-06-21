import pytest
from sqlalchemy import select
from app.modules.finanzas.models import Transaction, Category


@pytest.mark.asyncio
async def test_create_transaction(auth_client, db_session):
    response = await auth_client.post("/finanzas/transacciones/nueva", data={
        "amount": "1500.50",
        "type": "expense",
        "transaction_date": "2025-06-15",
        "product_name": "Supermercado",
        "merchant_name": "Jumbo",
        "payment_method": "debit_card",
        "notes": "Compra quincenal",
    })
    assert response.status_code == 303
    assert response.headers["location"] == "/finanzas/"

    result = await db_session.execute(
        select(Transaction).where(Transaction.product_name == "Supermercado")
    )
    txn = result.scalar_one_or_none()
    assert txn is not None
    assert txn.is_deleted is False


@pytest.mark.asyncio
async def test_create_transaction_income(auth_client, db_session):
    response = await auth_client.post("/finanzas/transacciones/nueva", data={
        "amount": "5000",
        "type": "income",
        "transaction_date": "2025-06-15",
        "product_name": "Salario",
    })
    assert response.status_code == 303

    result = await db_session.execute(
        select(Transaction).where(Transaction.product_name == "Salario")
    )
    txn = result.scalar_one_or_none()
    assert txn is not None
    assert txn.type == "income"


@pytest.mark.asyncio
async def test_create_transaction_with_category(auth_client, test_category, db_session):
    response = await auth_client.post("/finanzas/transacciones/nueva", data={
        "amount": "500",
        "type": "expense",
        "transaction_date": "2025-06-15",
        "product_name": "Cena",
        "category_id": test_category.id,
    })
    assert response.status_code == 303

    result = await db_session.execute(
        select(Transaction).where(Transaction.product_name == "Cena")
    )
    txn = result.scalar_one_or_none()
    assert txn is not None
    assert txn.category_id == test_category.id


@pytest.mark.asyncio
async def test_list_transactions(auth_client):
    response = await auth_client.get("/finanzas/transacciones")
    assert response.status_code == 200
    assert "Transacciones" in response.text


@pytest.mark.asyncio
async def test_list_transactions_with_pagination(auth_client):
    response = await auth_client.get("/finanzas/transacciones?page=1&per_page=10")
    assert response.status_code == 200
    assert "Transacciones" in response.text


@pytest.mark.asyncio
async def test_delete_transaction_soft_delete(auth_client, db_session):
    await auth_client.post("/finanzas/transacciones/nueva", data={
        "amount": "100",
        "type": "expense",
        "transaction_date": "2025-06-15",
        "product_name": "Para borrar",
    })

    result = await db_session.execute(
        select(Transaction).where(Transaction.product_name == "Para borrar")
    )
    txn = result.scalar_one_or_none()
    assert txn is not None

    response = await auth_client.post(f"/finanzas/transacciones/eliminar/{txn.id}")
    assert response.status_code == 303

    await db_session.refresh(txn)
    assert txn.is_deleted is True


@pytest.mark.asyncio
async def test_dashboard_shows_balance(auth_client):
    response = await auth_client.get("/finanzas/")
    assert response.status_code == 200
    assert "Balance" in response.text or "balance" in response.text.lower()


@pytest.mark.asyncio
async def test_dashboard_with_transactions(auth_client):
    await auth_client.post("/finanzas/transacciones/nueva", data={
        "amount": "1000",
        "type": "income",
        "transaction_date": "2025-06-15",
        "product_name": "Ingreso test",
    })
    response = await auth_client.get("/finanzas/")
    assert response.status_code == 200
    assert "Ingreso test" in response.text


@pytest.mark.asyncio
async def test_transaction_requires_auth(client):
    response = await client.get("/finanzas/transacciones", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_nueva_transaccion_form(auth_client):
    response = await auth_client.get("/finanzas/transacciones/nueva")
    assert response.status_code == 200
    assert "Nueva" in response.text


@pytest.mark.asyncio
async def test_create_transaction_negative_amount(auth_client, db_session):
    response = await auth_client.post("/finanzas/transacciones/nueva", data={
        "amount": "-100",
        "type": "expense",
        "transaction_date": "2025-06-15",
        "product_name": "Negativo",
    })
    assert response.status_code == 303
    assert response.headers["location"] == "/finanzas/transacciones/nueva"


@pytest.mark.asyncio
async def test_categorias_page(auth_client):
    response = await auth_client.get("/finanzas/categorias")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_categoria(auth_client, db_session):
    response = await auth_client.post("/finanzas/categorias", data={
        "name": "Transporte",
        "color": "#F59E0B",
        "icon": "fa-car",
    })
    assert response.status_code == 303

    result = await db_session.execute(
        select(Category).where(Category.name == "Transporte")
    )
    cat = result.scalar_one_or_none()
    assert cat is not None


@pytest.mark.asyncio
async def test_reportes_page(auth_client):
    response = await auth_client.get("/finanzas/reportes")
    assert response.status_code == 200

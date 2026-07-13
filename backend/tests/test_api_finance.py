import pytest
from sqlalchemy import select
from app.modules.finanzas.models import Transaction


@pytest.mark.asyncio
async def test_api_create_transaction(api_auth_client, db_session):
    response = await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "1500.50",
        "type": "expense",
        "transaction_date": "2025-06-15",
        "product_name": "Supermercado",
        "merchant_name": "Jumbo",
        "payment_method": "debit_card",
        "account_type": "checking",
        "notes": "Compra quincenal",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["product_name"] == "Supermercado"
    assert float(data["amount"]) == 1500.50
    assert data["is_deleted"] is False


@pytest.mark.asyncio
async def test_api_list_transactions(api_auth_client):
    await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "500",
        "type": "expense",
        "transaction_date": "2025-06-15",
        "product_name": "Test item",
        "account_type": "cash",
        "payment_method": "cash",
    })
    response = await api_auth_client.get("/api/v1/finance/transactions")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert len(data["items"]) >= 1
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_api_list_transactions_with_filters(api_auth_client):
    await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "100",
        "type": "income",
        "transaction_date": "2025-06-15",
        "product_name": "Salario",
        "account_type": "checking",
        "payment_method": "transfer",
    })
    response = await api_auth_client.get("/api/v1/finance/transactions?transaction_type=income")
    assert response.status_code == 200
    data = response.json()
    assert all(t["type"] == "income" for t in data["items"])


@pytest.mark.asyncio
async def test_api_update_transaction(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "200",
        "type": "expense",
        "transaction_date": "2025-06-15",
        "product_name": "Original",
        "account_type": "cash",
        "payment_method": "cash",
    })
    txn_id = create_resp.json()["id"]

    response = await api_auth_client.put(f"/api/v1/finance/transactions/{txn_id}", json={
        "product_name": "Actualizado",
        "amount": "300",
    })
    assert response.status_code == 200
    assert response.json()["product_name"] == "Actualizado"


@pytest.mark.asyncio
async def test_api_delete_transaction(api_auth_client, db_session):
    create_resp = await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "100",
        "type": "expense",
        "transaction_date": "2025-06-15",
        "product_name": "Para borrar",
        "account_type": "cash",
        "payment_method": "cash",
    })
    txn_id = create_resp.json()["id"]

    response = await api_auth_client.delete(f"/api/v1/finance/transactions/{txn_id}")
    assert response.status_code == 204

    result = await db_session.execute(
        select(Transaction).where(Transaction.id == txn_id)
    )
    txn = result.scalar_one_or_none()
    assert txn.is_deleted is True


@pytest.mark.asyncio
async def test_api_finance_summary(api_auth_client):
    await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "1000",
        "type": "income",
        "transaction_date": "2025-06-15",
        "product_name": "Ingreso",
        "account_type": "cash",
        "payment_method": "cash",
    })
    response = await api_auth_client.get("/api/v1/finance/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_income" in data
    assert "total_expenses" in data
    assert "balance" in data


@pytest.mark.asyncio
async def test_api_finance_categories(api_auth_client):
    response = await api_auth_client.get("/api/v1/finance/categories")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_api_finance_requires_auth(client):
    response = await client.get("/api/v1/finance/summary")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_update_nonexistent_transaction(api_auth_client):
    response = await api_auth_client.put("/api/v1/finance/transactions/nonexistent-id", json={
        "product_name": "No existe",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_delete_nonexistent_transaction(api_auth_client):
    response = await api_auth_client.delete("/api/v1/finance/transactions/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_soft_deleted_transaction_not_listed(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "250",
        "type": "expense",
        "transaction_date": "2025-07-01",
        "product_name": "Soft delete test",
        "account_type": "cash",
        "payment_method": "cash",
    })
    txn_id = create_resp.json()["id"]

    list_before = await api_auth_client.get("/api/v1/finance/transactions")
    ids_before = [t["id"] for t in list_before.json()["items"]]
    assert txn_id in ids_before

    await api_auth_client.delete(f"/api/v1/finance/transactions/{txn_id}")

    list_after = await api_auth_client.get("/api/v1/finance/transactions")
    ids_after = [t["id"] for t in list_after.json()["items"]]
    assert txn_id not in ids_after


@pytest.mark.asyncio
async def test_api_pagination_metadata(api_auth_client):
    for i in range(5):
        await api_auth_client.post("/api/v1/finance/transactions", json={
            "amount": str(100 + i),
            "type": "expense",
            "transaction_date": "2025-06-15",
            "product_name": f"Item {i}",
            "account_type": "cash",
            "payment_method": "cash",
        })

    response = await api_auth_client.get("/api/v1/finance/transactions?skip=0&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2

    response2 = await api_auth_client.get("/api/v1/finance/transactions?skip=2&limit=2")
    data2 = response2.json()
    assert len(data2["items"]) == 2
    assert data2["page"] == 2
    assert data2["items"][0]["id"] != data["items"][0]["id"]


@pytest.mark.asyncio
async def test_api_combined_filters(api_auth_client):
    await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "500",
        "type": "income",
        "transaction_date": "2025-06-01",
        "product_name": "Salario",
        "account_type": "checking",
        "payment_method": "transfer",
    })
    await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "200",
        "type": "expense",
        "transaction_date": "2025-06-15",
        "product_name": "Supermercado",
        "account_type": "cash",
        "payment_method": "cash",
    })

    response = await api_auth_client.get(
        "/api/v1/finance/transactions?date_from=2025-06-01&date_to=2025-06-30"
        "&transaction_type=expense"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["product_name"] == "Supermercado"

import pytest
from sqlalchemy import select
from app.modules.finanzas.models import Transaction, Budget


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
async def test_api_finance_summary_with_categorized_transaction(api_auth_client, test_category):
    await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "500",
        "type": "expense",
        "transaction_date": "2025-06-15",
        "product_name": "Compra categorizada",
        "account_type": "cash",
        "payment_method": "cash",
        "category_id": test_category.id,
    })
    response = await api_auth_client.get("/api/v1/finance/summary")
    assert response.status_code == 200
    data = response.json()
    assert float(data["total_expenses"]) == 500.0


@pytest.mark.asyncio
async def test_api_finance_categories(api_auth_client):
    response = await api_auth_client.get("/api/v1/finance/categories")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_api_create_category(api_auth_client):
    response = await api_auth_client.post("/api/v1/finance/categories", json={
        "name": "Transporte",
        "color": "#F59E0B",
        "icon": "fa-car",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Transporte"
    assert data["color"] == "#F59E0B"

    list_resp = await api_auth_client.get("/api/v1/finance/categories")
    assert any(c["name"] == "Transporte" for c in list_resp.json())


@pytest.mark.asyncio
async def test_api_update_category(api_auth_client, test_category):
    response = await api_auth_client.put(f"/api/v1/finance/categories/{test_category.id}", json={
        "name": "Renombrada",
        "color": "#EF4444",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Renombrada"
    assert data["color"] == "#EF4444"


@pytest.mark.asyncio
async def test_api_update_category_not_found(api_auth_client):
    response = await api_auth_client.put("/api/v1/finance/categories/does-not-exist", json={
        "name": "X",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_delete_category(api_auth_client, test_category, db_session):
    from app.modules.finanzas.models import Category

    response = await api_auth_client.delete(f"/api/v1/finance/categories/{test_category.id}")
    assert response.status_code == 204

    result = await db_session.execute(select(Category).where(Category.id == test_category.id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_api_delete_category_not_found(api_auth_client):
    response = await api_auth_client.delete("/api/v1/finance/categories/does-not-exist")
    assert response.status_code == 404


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


@pytest.mark.asyncio
async def test_api_create_budget(api_auth_client, test_category):
    response = await api_auth_client.post("/api/v1/finance/budgets", json={
        "category_id": test_category.id,
        "amount": "50000",
        "alert_threshold": 80,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["category_id"] == test_category.id
    assert float(data["amount"]) == 50000.0
    assert data["period"] == "monthly"


@pytest.mark.asyncio
async def test_api_list_budgets_with_progress(api_auth_client, test_category):
    await api_auth_client.post("/api/v1/finance/budgets", json={
        "category_id": test_category.id,
        "amount": "1000",
    })
    await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "300",
        "type": "expense",
        "transaction_date": "2025-06-10",
        "product_name": "Compra en categoria",
        "account_type": "cash",
        "payment_method": "cash",
        "category_id": test_category.id,
    })
    # Transaccion fuera del mes consultado: no debe sumar al gasto.
    await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "9999",
        "type": "expense",
        "transaction_date": "2025-05-10",
        "product_name": "Fuera de mes",
        "account_type": "cash",
        "payment_method": "cash",
        "category_id": test_category.id,
    })

    response = await api_auth_client.get(
        "/api/v1/finance/budgets", params={"year": 2025, "month": 6}
    )
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    item = items[0]
    assert item["category_name"] == test_category.name
    assert float(item["spent"]) == 300.0
    assert float(item["remaining"]) == 700.0
    assert item["percentage"] == pytest.approx(30.0)


@pytest.mark.asyncio
async def test_api_update_budget(api_auth_client, test_category):
    create_resp = await api_auth_client.post("/api/v1/finance/budgets", json={
        "category_id": test_category.id,
        "amount": "1000",
    })
    budget_id = create_resp.json()["id"]

    response = await api_auth_client.put(f"/api/v1/finance/budgets/{budget_id}", json={
        "amount": "2000",
        "alert_threshold": 90,
    })
    assert response.status_code == 200
    data = response.json()
    assert float(data["amount"]) == 2000.0
    assert data["alert_threshold"] == 90


@pytest.mark.asyncio
async def test_api_update_budget_not_found(api_auth_client):
    response = await api_auth_client.put("/api/v1/finance/budgets/does-not-exist", json={
        "amount": "1000",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_delete_budget(api_auth_client, test_category, db_session):
    create_resp = await api_auth_client.post("/api/v1/finance/budgets", json={
        "category_id": test_category.id,
        "amount": "1000",
    })
    budget_id = create_resp.json()["id"]

    response = await api_auth_client.delete(f"/api/v1/finance/budgets/{budget_id}")
    assert response.status_code == 204

    result = await db_session.execute(select(Budget).where(Budget.id == budget_id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_api_budgets_requires_auth(client):
    response = await client.get("/api/v1/finance/budgets", params={"year": 2025, "month": 6})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_finance_reports(api_auth_client, test_category):
    await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "500",
        "type": "expense",
        "transaction_date": "2025-06-15",
        "product_name": "Gasto categorizado",
        "account_type": "cash",
        "payment_method": "cash",
        "category_id": test_category.id,
    })
    await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "1000",
        "type": "income",
        "transaction_date": "2025-06-15",
        "product_name": "Ingreso",
        "account_type": "cash",
        "payment_method": "cash",
    })

    response = await api_auth_client.get("/api/v1/finance/reports")
    assert response.status_code == 200
    data = response.json()
    assert len(data["monthly"]) == 6
    assert any(c["name"] == test_category.name and float(c["total"]) == 500.0 for c in data["by_category"])
    assert float(data["total_expenses"]) == 500.0


@pytest.mark.asyncio
async def test_api_finance_reports_requires_auth(client):
    response = await client.get("/api/v1/finance/reports")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_create_bank_account(api_auth_client):
    response = await api_auth_client.post("/api/v1/finance/accounts", json={
        "name": "Cuenta sueldo",
        "bank_name": "Banco Nacion",
        "account_type": "checking",
        "account_number": "1234567890",
        "currency": "ARS",
        "balance": "10000",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Cuenta sueldo"
    assert data["account_type"] == "checking"
    assert data["last4"] == "7890"


@pytest.mark.asyncio
async def test_api_create_bank_account_invalid_type(api_auth_client):
    response = await api_auth_client.post("/api/v1/finance/accounts", json={
        "name": "Cuenta invalida",
        "account_type": "not-a-type",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_list_bank_accounts(api_auth_client):
    await api_auth_client.post("/api/v1/finance/accounts", json={
        "name": "Ahorros",
        "account_type": "savings",
    })
    response = await api_auth_client.get("/api/v1/finance/accounts")
    assert response.status_code == 200
    data = response.json()
    assert any(a["name"] == "Ahorros" for a in data)


@pytest.mark.asyncio
async def test_api_update_bank_account(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/finance/accounts", json={
        "name": "Original",
        "account_type": "cash",
    })
    account_id = create_resp.json()["id"]

    response = await api_auth_client.put(f"/api/v1/finance/accounts/{account_id}", json={
        "name": "Renombrada",
        "account_type": "investment",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Renombrada"
    assert data["account_type"] == "investment"


@pytest.mark.asyncio
async def test_api_update_bank_account_not_found(api_auth_client):
    response = await api_auth_client.put("/api/v1/finance/accounts/does-not-exist", json={
        "name": "X",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_delete_bank_account(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/finance/accounts", json={
        "name": "Para borrar",
        "account_type": "cash",
    })
    account_id = create_resp.json()["id"]

    response = await api_auth_client.delete(f"/api/v1/finance/accounts/{account_id}")
    assert response.status_code == 204

    list_resp = await api_auth_client.get("/api/v1/finance/accounts")
    assert all(a["id"] != account_id for a in list_resp.json())


@pytest.mark.asyncio
async def test_api_delete_bank_account_not_found(api_auth_client):
    response = await api_auth_client.delete("/api/v1/finance/accounts/does-not-exist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_accounts_requires_auth(client):
    response = await client.get("/api/v1/finance/accounts")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_create_transaction_rejects_invalid_payment_method(api_auth_client):
    # La web mandaba la etiqueta en español ("Efectivo") en vez del valor del
    # enum: antes esto rompia con 500 (ValueError en el service), ahora es 422.
    response = await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "100",
        "type": "expense",
        "transaction_date": "2026-09-22",
        "product_name": "Super",
        "account_type": "cash",
        "payment_method": "Efectivo",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_update_transaction_rejects_invalid_enum(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "100",
        "type": "expense",
        "transaction_date": "2026-09-22",
        "product_name": "Super",
        "account_type": "cash",
        "payment_method": "cash",
    })
    txn_id = create_resp.json()["id"]

    # Antes el update hacia setattr sin validar y guardaba el valor invalido.
    response = await api_auth_client.put(f"/api/v1/finance/transactions/{txn_id}", json={
        "payment_method": "Tarjeta",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_create_transaction_with_category_id(api_auth_client, test_category):
    response = await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "100",
        "type": "expense",
        "transaction_date": "2026-09-22",
        "product_name": "Super",
        "account_type": "cash",
        "payment_method": "debit_card",
        "category_id": test_category.id,
    })
    assert response.status_code == 201
    assert response.json()["category_id"] == test_category.id


@pytest.mark.asyncio
async def test_api_update_transaction_can_clear_category(api_auth_client, test_category):
    create_resp = await api_auth_client.post("/api/v1/finance/transactions", json={
        "amount": "100",
        "type": "expense",
        "transaction_date": "2026-09-22",
        "product_name": "Super",
        "account_type": "cash",
        "payment_method": "cash",
        "category_id": test_category.id,
        "notes": "nota cargada desde mobile",
    })
    txn_id = create_resp.json()["id"]

    # null explicito = "Sin categoria". Antes el service ignoraba cualquier
    # None y la categoria no se podia quitar nunca.
    response = await api_auth_client.put(f"/api/v1/finance/transactions/{txn_id}", json={
        "category_id": None,
    })
    assert response.status_code == 200
    assert response.json()["category_id"] is None
    # Lo que no se mando no se toca.
    assert response.json()["notes"] == "nota cargada desde mobile"


# ── Inversiones: campos aditivos del resumen y patrimonio ───────────────────


async def _income(client, amount):
    resp = await client.post("/api/v1/finance/transactions", json={
        "amount": str(amount),
        "type": "income",
        "transaction_date": "2025-06-15",
        "product_name": "Ingreso",
        "account_type": "cash",
        "payment_method": "cash",
    })
    assert resp.status_code == 201, resp.text


async def _investment(client, **overrides):
    body = {
        "asset_type": "stock",
        "name": "Activo",
        "currency": "ARS",
        "invested_amount": "100",
    }
    body.update(overrides)
    resp = await client.post("/api/v1/finance/investments", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_summary_sin_inversiones_mantiene_balance_y_suma_campos(api_auth_client):
    await _income(api_auth_client, 1000)
    data = (await api_auth_client.get("/api/v1/finance/summary")).json()
    assert float(data["balance"]) == 1000
    assert float(data["investments_value_ars"]) == 0
    assert float(data["net_worth_ars"]) == 1000
    assert data["investments_missing_rates"] == []
    assert data["include_investments_in_balance"] is False


@pytest.mark.asyncio
async def test_summary_el_toggle_no_cambia_el_balance(api_auth_client):
    await _income(api_auth_client, 100000)
    await _investment(api_auth_client, invested_amount="500000", current_value="500000")

    off = (await api_auth_client.get("/api/v1/finance/summary")).json()
    resp = await api_auth_client.put("/api/v1/settings", json={"include_investments_in_balance": True})
    assert resp.json()["include_investments_in_balance"] is True
    on = (await api_auth_client.get("/api/v1/finance/summary")).json()

    assert off["balance"] == on["balance"]
    assert float(on["balance"]) == 100000
    assert float(on["investments_value_ars"]) == 500000
    assert float(on["net_worth_ars"]) == 600000
    assert off["include_investments_in_balance"] is False
    assert on["include_investments_in_balance"] is True


@pytest.mark.asyncio
async def test_summary_con_cotizacion_faltante_devuelve_null(api_auth_client):
    await _income(api_auth_client, 1000)
    await _investment(api_auth_client, currency="USD")
    data = (await api_auth_client.get("/api/v1/finance/summary")).json()
    assert float(data["balance"]) == 1000
    assert data["investments_value_ars"] is None
    assert data["net_worth_ars"] is None
    assert data["investments_missing_rates"] == ["USD"]


@pytest.mark.asyncio
async def test_summary_solo_ars_sin_cotizacion_no_pide_cotizacion(api_auth_client):
    await _investment(api_auth_client, current_value="250")
    data = (await api_auth_client.get("/api/v1/finance/summary")).json()
    assert float(data["investments_value_ars"]) == 250
    assert data["investments_missing_rates"] == []


@pytest.mark.asyncio
async def test_summary_acepta_tz_offset_y_lo_valida(api_auth_client):
    ok = await api_auth_client.get("/api/v1/finance/summary", params={"tz_offset_minutes": -180})
    assert ok.status_code == 200
    bad = await api_auth_client.get("/api/v1/finance/summary", params={"tz_offset_minutes": 841})
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_net_worth_suma_balance_e_inversiones_activas(api_auth_client):
    from decimal import Decimal as D

    await api_auth_client.put("/api/v1/settings", json={"fx_usd_ars": "1450.50"})
    await _income(api_auth_client, 100000)
    await _investment(api_auth_client, name="Pesos", current_value="500000")
    await _investment(
        api_auth_client, name="Dolares", currency="USD", asset_type="fx",
        invested_amount="1800", current_value="2000",
    )

    data = (await api_auth_client.get("/api/v1/finance/net-worth")).json()
    assert D(data["cash_balance_ars"]) == D("100000.00")
    assert D(data["cash_balance_usd"]) == D("68.94")
    assert D(data["investments"]["total_ars"]) == D("3401000.00")
    assert D(data["investments"]["total_usd"]) == D("2344.71")
    assert D(data["net_worth_ars"]) == D("3501000.00")
    assert D(data["net_worth_usd"]) == D("2413.65")
    assert D(data["rates"]["usd_ars"]) == D("1450.5000")
    assert data["rates"]["eur_ars"] is None
    assert data["rates"]["updated_at"] is not None
    assert data["missing_rates"] == []
    assert data["include_investments_in_balance"] is False


@pytest.mark.asyncio
async def test_net_worth_sin_cotizacion_conserva_la_parte_en_pesos(api_auth_client):
    from decimal import Decimal as D

    await _income(api_auth_client, 100000)
    await _investment(api_auth_client, current_value="500000")
    data = (await api_auth_client.get("/api/v1/finance/net-worth")).json()
    assert D(data["cash_balance_ars"]) == D("100000.00")
    assert D(data["investments"]["total_ars"]) == D("500000.00")
    assert D(data["net_worth_ars"]) == D("600000.00")
    assert data["cash_balance_usd"] is None
    assert data["investments"]["total_usd"] is None
    assert data["net_worth_usd"] is None
    assert data["missing_rates"] == ["USD"]


@pytest.mark.asyncio
async def test_net_worth_con_dolares_sin_cotizacion_deja_ars_en_null(api_auth_client):
    await _income(api_auth_client, 100000)
    await _investment(api_auth_client, currency="USD", current_value="100")
    data = (await api_auth_client.get("/api/v1/finance/net-worth")).json()
    assert float(data["cash_balance_ars"]) == 100000
    assert data["net_worth_ars"] is None
    assert data["net_worth_usd"] is None
    assert data["missing_rates"] == ["USD"]


@pytest.mark.asyncio
async def test_net_worth_cerrar_una_inversion_la_descuenta(api_auth_client):
    await _income(api_auth_client, 1000)
    inv = await _investment(api_auth_client, current_value="500")
    before = (await api_auth_client.get("/api/v1/finance/net-worth")).json()
    await api_auth_client.put(f"/api/v1/finance/investments/{inv['id']}", json={"status": "closed"})
    after = (await api_auth_client.get("/api/v1/finance/net-worth")).json()
    assert float(before["net_worth_ars"]) - float(after["net_worth_ars"]) == 500


@pytest.mark.asyncio
async def test_net_worth_usuario_nuevo_en_cero(api_auth_client):
    data = (await api_auth_client.get("/api/v1/finance/net-worth")).json()
    assert float(data["cash_balance_ars"]) == 0
    assert float(data["net_worth_ars"]) == 0
    assert data["investments"]["count_active"] == 0

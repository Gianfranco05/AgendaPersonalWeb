import pytest


@pytest.mark.asyncio
async def test_api_create_meal(api_auth_client):
    response = await api_auth_client.post("/api/v1/nutrition/meals", json={
        "meal_date": "2026-07-06",
        "meal_type": "lunch",
        "name": "Pollo con arroz",
        "calories": 620,
        "protein_g": 45,
        "carbs_g": 70,
        "fat_g": 12,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Pollo con arroz"
    assert data["meal_date"] == "2026-07-06"
    assert data["meal_type"] == "lunch"


@pytest.mark.asyncio
async def test_api_list_meals(api_auth_client):
    await api_auth_client.post("/api/v1/nutrition/meals", json={
        "meal_date": "2026-07-05",
        "meal_type": "breakfast",
        "name": "Avena",
    })
    response = await api_auth_client.get("/api/v1/nutrition/meals")
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_api_list_meals_date_filter(api_auth_client):
    await api_auth_client.post("/api/v1/nutrition/meals", json={
        "meal_date": "2026-06-01", "meal_type": "dinner", "name": "Vieja",
    })
    await api_auth_client.post("/api/v1/nutrition/meals", json={
        "meal_date": "2026-07-10", "meal_type": "dinner", "name": "Nueva",
    })
    response = await api_auth_client.get(
        "/api/v1/nutrition/meals?date_from=2026-07-01&date_to=2026-07-31"
    )
    assert response.status_code == 200
    names = [m["name"] for m in response.json()]
    assert "Nueva" in names
    assert "Vieja" not in names


@pytest.mark.asyncio
async def test_api_get_meal_not_found(api_auth_client):
    response = await api_auth_client.get("/api/v1/nutrition/meals/nope")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_update_meal(api_auth_client):
    create = await api_auth_client.post("/api/v1/nutrition/meals", json={
        "meal_date": "2026-07-06", "meal_type": "snack", "name": "Yogur", "calories": 100,
    })
    meal_id = create.json()["id"]
    response = await api_auth_client.put(f"/api/v1/nutrition/meals/{meal_id}", json={
        "name": "Yogur con nueces", "calories": 260,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Yogur con nueces"
    assert data["calories"] == 260


@pytest.mark.asyncio
async def test_api_delete_meal(api_auth_client):
    create = await api_auth_client.post("/api/v1/nutrition/meals", json={
        "meal_date": "2026-07-06", "meal_type": "lunch", "name": "Borrar",
    })
    meal_id = create.json()["id"]
    delete = await api_auth_client.delete(f"/api/v1/nutrition/meals/{meal_id}")
    assert delete.status_code == 204
    get = await api_auth_client.get(f"/api/v1/nutrition/meals/{meal_id}")
    assert get.status_code == 404


@pytest.mark.asyncio
async def test_api_nutrition_summary(api_auth_client):
    response = await api_auth_client.get("/api/v1/nutrition/summary")
    assert response.status_code == 200
    data = response.json()
    for key in (
        "today_calories", "today_protein_g", "today_carbs_g", "today_fat_g",
        "week_calories", "week_protein_g", "week_carbs_g", "week_fat_g",
    ):
        assert key in data


@pytest.mark.asyncio
async def test_api_nutrition_requires_auth(client):
    response = await client.get("/api/v1/nutrition/meals")
    assert response.status_code == 401

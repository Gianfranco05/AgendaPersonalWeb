import pytest
from sqlalchemy import select
from app.modules.metas.models import Goal, HabitRecord


@pytest.mark.asyncio
async def test_create_goal(auth_client, db_session):
    response = await auth_client.post("/metas/nueva", data={
        "title": "Ejercicio diario",
        "description": "Hacer ejercicio todos los dias",
        "goal_type": "binary",
        "target_value": "30",
        "unit": "dias",
        "color": "#7C3AED",
        "icon": "fa-dumbbell",
    })
    assert response.status_code == 303
    assert response.headers["location"] == "/metas/"

    result = await db_session.execute(
        select(Goal).where(Goal.title == "Ejercicio diario")
    )
    goal = result.scalar_one_or_none()
    assert goal is not None
    assert goal.goal_type == "binary"
    assert goal.target_value == 30


@pytest.mark.asyncio
async def test_list_goals(auth_client):
    response = await auth_client.get("/metas/")
    assert response.status_code == 200
    assert "Metas" in response.text


@pytest.mark.asyncio
async def test_list_goals_empty(auth_client):
    response = await auth_client.get("/metas/")
    assert response.status_code == 200
    assert "No hay metas activas" in response.text


@pytest.mark.asyncio
async def test_checkin_habit(auth_client, db_session):
    await auth_client.post("/metas/nueva", data={
        "title": "Leer",
        "goal_type": "binary",
        "target_value": "30",
    })

    result = await db_session.execute(
        select(Goal).where(Goal.title == "Leer")
    )
    goal = result.scalar_one_or_none()
    assert goal is not None

    response = await auth_client.post(f"/metas/registrar/{goal.id}", data={
        "value": "1",
        "notes": "Lei 30 minutos",
    })
    assert response.status_code == 303

    records_result = await db_session.execute(
        select(HabitRecord).where(HabitRecord.goal_id == goal.id)
    )
    records = records_result.scalars().all()
    assert len(records) == 1
    assert records[0].value == 1


@pytest.mark.asyncio
async def test_complete_goal(auth_client, db_session):
    await auth_client.post("/metas/nueva", data={
        "title": "Meditar",
        "goal_type": "binary",
        "target_value": "1",
    })

    result = await db_session.execute(
        select(Goal).where(Goal.title == "Meditar")
    )
    goal = result.scalar_one_or_none()
    assert goal is not None

    response = await auth_client.post(f"/metas/completar/{goal.id}")
    assert response.status_code == 303

    await db_session.refresh(goal)
    assert goal.is_completed is True


@pytest.mark.asyncio
async def test_edit_goal(auth_client, db_session):
    await auth_client.post("/metas/nueva", data={
        "title": "Meta original",
        "goal_type": "binary",
        "target_value": "10",
    })

    result = await db_session.execute(
        select(Goal).where(Goal.title == "Meta original")
    )
    goal = result.scalar_one_or_none()
    assert goal is not None

    response = await auth_client.post(f"/metas/editar/{goal.id}", data={
        "title": "Meta editada",
        "goal_type": "progress",
        "target_value": "20",
        "action": "save",
    })
    assert response.status_code == 303

    await db_session.refresh(goal)
    assert goal.title == "Meta editada"
    assert goal.target_value == 20


@pytest.mark.asyncio
async def test_delete_goal(auth_client, db_session):
    await auth_client.post("/metas/nueva", data={
        "title": "Para borrar",
        "goal_type": "binary",
        "target_value": "1",
    })

    result = await db_session.execute(
        select(Goal).where(Goal.title == "Para borrar")
    )
    goal = result.scalar_one_or_none()
    assert goal is not None

    response = await auth_client.post(f"/metas/editar/{goal.id}", data={
        "title": "Para borrar",
        "action": "delete",
    })
    assert response.status_code == 303

    result = await db_session.execute(
        select(Goal).where(Goal.id == goal.id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_goal_requires_auth(client):
    response = await client.get("/metas/", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_nueva_meta_form(auth_client):
    response = await auth_client.get("/metas/nueva")
    assert response.status_code == 200
    assert "Nueva Meta" in response.text


@pytest.mark.asyncio
async def test_api_goals(auth_client, db_session):
    await auth_client.post("/metas/nueva", data={
        "title": "API Goal",
        "goal_type": "binary",
        "target_value": "5",
    })

    response = await auth_client.get("/metas/api/goals")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(g["title"] == "API Goal" for g in data)


@pytest.mark.asyncio
async def test_api_v1_goals_create_and_list(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/goals", json={
        "title": "V1 API Goal",
        "goal_type": "binary",
        "description": "Test via v1 API",
    })
    assert create_resp.status_code == 201
    goal = create_resp.json()
    assert goal["title"] == "V1 API Goal"
    assert goal["progress"] == 0.0

    list_resp = await api_auth_client.get("/api/v1/goals")
    assert list_resp.status_code == 200
    assert any(g["title"] == "V1 API Goal" for g in list_resp.json())


@pytest.mark.asyncio
async def test_api_v1_goals_update(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/goals", json={
        "title": "Meta a editar",
        "goal_type": "progress",
        "target_value": 10,
        "unit": "veces",
    })
    goal_id = create_resp.json()["id"]

    update_resp = await api_auth_client.put(f"/api/v1/goals/{goal_id}", json={
        "title": "Meta editada",
        "unit": "km",
    })
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["title"] == "Meta editada"
    assert updated["unit"] == "km"
    # campos no enviados no se tocan
    assert updated["target_value"] == 10.0


@pytest.mark.asyncio
async def test_api_v1_goals_update_not_found(api_auth_client):
    resp = await api_auth_client.put("/api/v1/goals/does-not-exist", json={"title": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_v1_goals_delete(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/goals", json={
        "title": "Meta a borrar",
        "goal_type": "binary",
    })
    goal_id = create_resp.json()["id"]

    delete_resp = await api_auth_client.delete(f"/api/v1/goals/{goal_id}")
    assert delete_resp.status_code == 204

    list_resp = await api_auth_client.get("/api/v1/goals")
    assert all(g["id"] != goal_id for g in list_resp.json())


@pytest.mark.asyncio
async def test_api_v1_goals_delete_not_found(api_auth_client):
    resp = await api_auth_client.delete("/api/v1/goals/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_v1_goals_habit_checkin(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/goals", json={
        "title": "Habit Goal",
        "goal_type": "progress",
        "target_value": 10,
        "unit": "veces",
    })
    goal_id = create_resp.json()["id"]

    checkin = await api_auth_client.put(f"/api/v1/goals/{goal_id}/checkin", json={
        "record_date": "2025-07-01",
        "value": 1,
    })
    assert checkin.status_code == 200
    updated = checkin.json()
    assert updated["current_value"] == 1.0
    assert updated["progress"] == 10.0


@pytest.mark.asyncio
async def test_api_v1_goals_records_and_monthly_summary(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/goals", json={
        "title": "Entrenamiento",
        "goal_type": "metric",
        "unit": "minutos",
    })
    goal_id = create_resp.json()["id"]

    r1 = await api_auth_client.post(f"/api/v1/goals/{goal_id}/records", json={
        "record_date": "2026-07-01",
        "value": 45,
    })
    assert r1.status_code == 201
    assert r1.json()["value"] == 45.0

    # Upsert: cargar de nuevo el mismo dia reemplaza el valor, no duplica.
    r2 = await api_auth_client.post(f"/api/v1/goals/{goal_id}/records", json={
        "record_date": "2026-07-01",
        "value": 60,
    })
    assert r2.status_code == 201
    assert r2.json()["value"] == 60.0

    r3 = await api_auth_client.post(f"/api/v1/goals/{goal_id}/records", json={
        "record_date": "2026-07-02",
        "value": 30,
    })
    assert r3.status_code == 201

    records_resp = await api_auth_client.get(
        f"/api/v1/goals/{goal_id}/records", params={"year": 2026, "month": 7}
    )
    assert records_resp.status_code == 200
    records = records_resp.json()
    assert len(records) == 2
    assert sum(rec["value"] for rec in records) == 90.0

    summary_resp = await api_auth_client.get(
        "/api/v1/goals/summary/monthly", params={"year": 2026, "month": 7}
    )
    assert summary_resp.status_code == 200
    item = next(s for s in summary_resp.json() if s["goal_id"] == goal_id)
    assert item["total"] == 90.0
    # promedio estilo Excel: total / dias del mes (julio tiene 31), no AVG sobre dias registrados
    assert item["average"] == pytest.approx(90.0 / 31)


@pytest.mark.asyncio
async def test_api_v1_goals_records_requires_valid_goal(api_auth_client):
    resp = await api_auth_client.get(
        "/api/v1/goals/does-not-exist/records", params={"year": 2026, "month": 7}
    )
    assert resp.status_code == 404

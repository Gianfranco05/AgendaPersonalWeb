import pytest


@pytest.mark.asyncio
async def test_api_create_session_with_exercises(api_auth_client):
    response = await api_auth_client.post("/api/v1/fitness/sessions", json={
        "title": "Tren superior",
        "session_date": "2026-07-06",
        "duration_minutes": 60,
        "notes": "Buen ritmo",
        "exercises": [
            {"name": "Press banca", "sets": 4, "reps": 8, "weight_kg": 60, "order": 0},
            {"name": "Remo", "sets": 4, "reps": 10, "weight_kg": 50, "order": 1},
        ],
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Tren superior"
    assert data["session_date"] == "2026-07-06"
    assert len(data["exercises"]) == 2
    assert data["exercises"][0]["name"] == "Press banca"


@pytest.mark.asyncio
async def test_api_list_sessions(api_auth_client):
    await api_auth_client.post("/api/v1/fitness/sessions", json={
        "title": "Piernas",
        "session_date": "2026-07-05",
    })
    response = await api_auth_client.get("/api/v1/fitness/sessions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_api_get_session(api_auth_client):
    create = await api_auth_client.post("/api/v1/fitness/sessions", json={
        "title": "Cardio",
        "session_date": "2026-07-04",
    })
    session_id = create.json()["id"]
    response = await api_auth_client.get(f"/api/v1/fitness/sessions/{session_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Cardio"


@pytest.mark.asyncio
async def test_api_get_session_not_found(api_auth_client):
    response = await api_auth_client.get("/api/v1/fitness/sessions/does-not-exist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_update_session_replaces_exercises(api_auth_client):
    create = await api_auth_client.post("/api/v1/fitness/sessions", json={
        "title": "Original",
        "session_date": "2026-07-01",
        "exercises": [{"name": "Sentadilla", "sets": 5, "reps": 5, "order": 0}],
    })
    session_id = create.json()["id"]
    response = await api_auth_client.put(f"/api/v1/fitness/sessions/{session_id}", json={
        "title": "Actualizada",
        "exercises": [
            {"name": "Peso muerto", "sets": 3, "reps": 6, "order": 0},
            {"name": "Zancadas", "sets": 3, "reps": 12, "order": 1},
        ],
    })
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Actualizada"
    assert len(data["exercises"]) == 2
    assert {e["name"] for e in data["exercises"]} == {"Peso muerto", "Zancadas"}


@pytest.mark.asyncio
async def test_api_delete_session(api_auth_client):
    create = await api_auth_client.post("/api/v1/fitness/sessions", json={
        "title": "Borrar",
        "session_date": "2026-07-02",
    })
    session_id = create.json()["id"]
    delete = await api_auth_client.delete(f"/api/v1/fitness/sessions/{session_id}")
    assert delete.status_code == 204
    get = await api_auth_client.get(f"/api/v1/fitness/sessions/{session_id}")
    assert get.status_code == 404


@pytest.mark.asyncio
async def test_api_fitness_summary(api_auth_client):
    await api_auth_client.post("/api/v1/fitness/sessions", json={
        "title": "S1",
        "session_date": "2026-07-06",
        "exercises": [{"name": "A", "order": 0}, {"name": "B", "order": 1}],
    })
    response = await api_auth_client.get("/api/v1/fitness/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_exercises"] >= 2
    assert "sessions_this_month" in data


@pytest.mark.asyncio
async def test_api_fitness_requires_auth(client):
    response = await client.get("/api/v1/fitness/sessions")
    assert response.status_code == 401

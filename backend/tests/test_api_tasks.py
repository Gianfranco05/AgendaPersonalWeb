import pytest


@pytest.mark.asyncio
async def test_api_create_task(api_auth_client):
    response = await api_auth_client.post("/api/v1/tasks", json={
        "title": "Enviar propuesta a cliente X",
        "area": "Trabajo",
        "priority": "alta",
        "due_date": "2026-07-20",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Enviar propuesta a cliente X"
    assert data["area"] == "Trabajo"
    assert data["priority"] == "alta"
    assert data["status"] == "pending"
    assert data["order"] == 0


@pytest.mark.asyncio
async def test_api_list_tasks_filters_by_area_and_status(api_auth_client):
    await api_auth_client.post("/api/v1/tasks", json={"title": "Tarea trabajo", "area": "Trabajo"})
    await api_auth_client.post("/api/v1/tasks", json={"title": "Renovar DNI", "area": "Otras Tareas"})

    response = await api_auth_client.get("/api/v1/tasks", params={"area": "Trabajo"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Tarea trabajo"

    response = await api_auth_client.get("/api/v1/tasks", params={"status": "pending"})
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_api_update_task(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/tasks", json={"title": "Original"})
    task_id = create_resp.json()["id"]

    response = await api_auth_client.patch(f"/api/v1/tasks/{task_id}", json={
        "title": "Editada",
        "priority": "baja",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Editada"
    assert data["priority"] == "baja"


@pytest.mark.asyncio
async def test_api_delete_task(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/tasks", json={"title": "Para borrar"})
    task_id = create_resp.json()["id"]

    response = await api_auth_client.delete(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 204

    list_resp = await api_auth_client.get("/api/v1/tasks")
    assert all(t["id"] != task_id for t in list_resp.json())


@pytest.mark.asyncio
async def test_api_move_task_reindexes_destination_column(api_auth_client):
    ids = []
    for title in ["Uno", "Dos", "Tres"]:
        resp = await api_auth_client.post("/api/v1/tasks", json={"title": title, "status": "pending"})
        ids.append(resp.json()["id"])

    move_resp = await api_auth_client.post(f"/api/v1/tasks/{ids[2]}/move", json={
        "status": "in_progress",
        "order": 0,
    })
    assert move_resp.status_code == 200
    moved = move_resp.json()
    assert moved["status"] == "in_progress"
    assert moved["order"] == 0

    remaining = await api_auth_client.get("/api/v1/tasks", params={"status": "pending"})
    remaining_orders = sorted(t["order"] for t in remaining.json())
    assert remaining_orders == [0, 1]


@pytest.mark.asyncio
async def test_api_task_requires_auth(client):
    response = await client.get("/api/v1/tasks")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_task_not_found(api_auth_client):
    response = await api_auth_client.patch("/api/v1/tasks/does-not-exist", json={"title": "X"})
    assert response.status_code == 404

    response = await api_auth_client.delete("/api/v1/tasks/does-not-exist")
    assert response.status_code == 404

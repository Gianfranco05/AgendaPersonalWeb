import pytest


@pytest.mark.asyncio
async def test_api_create_event(api_auth_client):
    response = await api_auth_client.post("/api/v1/events", json={
        "title": "Reunion",
        "description": "Reunion de equipo",
        "start_datetime": "2025-07-01T10:00:00",
        "end_datetime": "2025-07-01T11:00:00",
        "color": "#3b82f6",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Reunion"


@pytest.mark.asyncio
async def test_api_list_events(api_auth_client):
    await api_auth_client.post("/api/v1/events", json={
        "title": "Evento test",
        "start_datetime": "2025-07-15T14:00:00",
    })
    response = await api_auth_client.get("/api/v1/events")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_api_list_events_with_date_range(api_auth_client):
    await api_auth_client.post("/api/v1/events", json={
        "title": "Evento julio",
        "start_datetime": "2025-07-20T10:00:00",
    })
    response = await api_auth_client.get("/api/v1/events?date_from=2025-07-01&date_to=2025-07-31")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_api_update_event(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/events", json={
        "title": "Original",
        "start_datetime": "2025-08-01T10:00:00",
    })
    event_id = create_resp.json()["id"]

    response = await api_auth_client.put(f"/api/v1/events/{event_id}", json={
        "title": "Actualizado",
    })
    assert response.status_code == 200
    assert response.json()["title"] == "Actualizado"


@pytest.mark.asyncio
async def test_api_delete_event(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/events", json={
        "title": "Para borrar",
        "start_datetime": "2025-08-01T10:00:00",
    })
    event_id = create_resp.json()["id"]

    response = await api_auth_client.delete(f"/api/v1/events/{event_id}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_api_events_requires_auth(client):
    response = await client.get("/api/v1/events")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_update_nonexistent_event(api_auth_client):
    response = await api_auth_client.put("/api/v1/events/nonexistent-id", json={
        "title": "No existe",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_delete_nonexistent_event(api_auth_client):
    response = await api_auth_client.delete("/api/v1/events/nonexistent-id")
    assert response.status_code == 404

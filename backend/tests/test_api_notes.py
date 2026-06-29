import pytest


@pytest.mark.asyncio
async def test_api_create_note(api_auth_client):
    response = await api_auth_client.post("/api/v1/notes", json={
        "title": "Mi nota",
        "content": "Contenido de prueba",
        "color": "#ffffff",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Mi nota"
    assert data["content"] == "Contenido de prueba"


@pytest.mark.asyncio
async def test_api_create_note_with_tags(api_auth_client):
    response = await api_auth_client.post("/api/v1/notes", json={
        "title": "Nota con tags",
        "content": "Contenido",
        "tag_names": ["trabajo", "importante"],
    })
    assert response.status_code == 201
    data = response.json()
    assert len(data["tags"]) == 2


@pytest.mark.asyncio
async def test_api_list_notes(api_auth_client):
    await api_auth_client.post("/api/v1/notes", json={
        "title": "Nota 1",
        "content": "Contenido 1",
    })
    response = await api_auth_client.get("/api/v1/notes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_api_list_notes_search(api_auth_client):
    await api_auth_client.post("/api/v1/notes", json={
        "title": "Buscarme",
        "content": "Contenido unico xyz",
    })
    response = await api_auth_client.get("/api/v1/notes?search=xyz")
    assert response.status_code == 200
    data = response.json()
    assert any("xyz" in n["content"] for n in data)


@pytest.mark.asyncio
async def test_api_update_note(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/notes", json={
        "title": "Original",
        "content": "Contenido original",
    })
    note_id = create_resp.json()["id"]

    response = await api_auth_client.put(f"/api/v1/notes/{note_id}", json={
        "title": "Actualizada",
        "is_pinned": True,
    })
    assert response.status_code == 200
    assert response.json()["title"] == "Actualizada"
    assert response.json()["is_pinned"] is True


@pytest.mark.asyncio
async def test_api_delete_note(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/notes", json={
        "title": "Para borrar",
        "content": "Borrar",
    })
    note_id = create_resp.json()["id"]

    response = await api_auth_client.delete(f"/api/v1/notes/{note_id}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_api_list_tags(api_auth_client):
    await api_auth_client.post("/api/v1/notes", json={
        "title": "Nota con tag",
        "content": "Contenido",
        "tag_names": ["tagtest"],
    })
    response = await api_auth_client.get("/api/v1/notes/tags")
    assert response.status_code == 200
    data = response.json()
    assert any(t["name"] == "tagtest" for t in data)


@pytest.mark.asyncio
async def test_api_notes_requires_auth(client):
    response = await client.get("/api/v1/notes")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_update_nonexistent_note(api_auth_client):
    response = await api_auth_client.put("/api/v1/notes/nonexistent-id", json={
        "title": "No existe",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_delete_nonexistent_note(api_auth_client):
    response = await api_auth_client.delete("/api/v1/notes/nonexistent-id")
    assert response.status_code == 404

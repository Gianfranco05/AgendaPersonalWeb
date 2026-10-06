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


@pytest.mark.asyncio
async def test_api_notes_crud_full(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/notes", json={
        "title": "CRUD test",
        "content": "CRUD content",
        "color": "#ff0000",
        "tag_names": ["test-tag"],
    })
    assert create_resp.status_code == 201
    note = create_resp.json()
    note_id = note["id"]
    assert note["title"] == "CRUD test"
    assert note["content"] == "CRUD content"
    assert len(note["tags"]) == 1

    get_resp = await api_auth_client.get("/api/v1/notes")
    assert get_resp.status_code == 200
    assert any(n["id"] == note_id for n in get_resp.json())

    update_resp = await api_auth_client.put(f"/api/v1/notes/{note_id}", json={
        "title": "Updated CRUD",
        "is_pinned": True,
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Updated CRUD"
    assert update_resp.json()["is_pinned"] is True

    delete_resp = await api_auth_client.delete(f"/api/v1/notes/{note_id}")
    assert delete_resp.status_code == 204

    get_after = await api_auth_client.get("/api/v1/notes")
    assert all(n["id"] != note_id for n in get_after.json())


@pytest.mark.asyncio
async def test_api_export_notes_json(api_auth_client):
    await api_auth_client.post("/api/v1/notes", json={
        "title": "Nota exportable",
        "content": "Contenido exportable",
        "tag_names": ["export"],
    })
    archived = await api_auth_client.post("/api/v1/notes", json={
        "title": "Nota archivada",
        "content": "No deberia aparecer",
    })
    archived_id = archived.json()["id"]
    await api_auth_client.put(f"/api/v1/notes/{archived_id}", json={"is_archived": True})

    response = await api_auth_client.get("/api/v1/notes/export/json")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "notas.json" in response.headers["content-disposition"]
    data = response.json()
    titles = [n["title"] for n in data]
    assert "Nota exportable" in titles
    assert "Nota archivada" not in titles
    exported = next(n for n in data if n["title"] == "Nota exportable")
    assert exported["tags"] == ["export"]


@pytest.mark.asyncio
async def test_api_export_notes_json_requires_auth(client):
    response = await client.get("/api/v1/notes/export/json")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_update_note_replaces_tags(api_auth_client):
    # Antes NoteUpdate no tenia campo de tags: una vez creada la nota, sus
    # tags no se podian cambiar nunca, ni desde web ni desde mobile.
    create_resp = await api_auth_client.post("/api/v1/notes", json={
        "title": "Con tags", "content": "x", "tag_names": ["viejo", "comun"],
    })
    note_id = create_resp.json()["id"]

    response = await api_auth_client.put(f"/api/v1/notes/{note_id}", json={
        "tag_names": ["comun", "nuevo", "nuevo", "  "],
    })
    assert response.status_code == 200
    assert sorted(t["name"] for t in response.json()["tags"]) == ["comun", "nuevo"]

    listed = await api_auth_client.get("/api/v1/notes")
    note = next(n for n in listed.json() if n["id"] == note_id)
    assert sorted(t["name"] for t in note["tags"]) == ["comun", "nuevo"]


@pytest.mark.asyncio
async def test_api_update_note_empty_list_clears_tags(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/notes", json={
        "title": "Con tags", "content": "x", "tag_names": ["a"],
    })
    note_id = create_resp.json()["id"]

    response = await api_auth_client.put(f"/api/v1/notes/{note_id}", json={"tag_names": []})
    assert response.status_code == 200
    assert response.json()["tags"] == []


@pytest.mark.asyncio
async def test_api_update_note_without_tag_names_keeps_tags(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/notes", json={
        "title": "Con tags", "content": "x", "tag_names": ["queda"],
    })
    note_id = create_resp.json()["id"]

    response = await api_auth_client.put(f"/api/v1/notes/{note_id}", json={"title": "Otro titulo"})
    assert response.status_code == 200
    assert response.json()["title"] == "Otro titulo"
    assert [t["name"] for t in response.json()["tags"]] == ["queda"]


@pytest.mark.asyncio
async def test_create_note_respeta_is_pinned(api_auth_client):
    created = await api_auth_client.post(
        "/api/v1/notes", json={"title": "Fijada", "content": "x", "is_pinned": True}
    )
    assert created.status_code == 201
    assert created.json()["is_pinned"] is True

    # Compatible con el cliente que crea y despues fija con un PUT.
    other = await api_auth_client.post("/api/v1/notes", json={"title": "Normal", "content": "x"})
    assert other.json()["is_pinned"] is False
    pinned = await api_auth_client.put(
        f"/api/v1/notes/{other.json()['id']}", json={"is_pinned": True}
    )
    assert pinned.json()["is_pinned"] is True

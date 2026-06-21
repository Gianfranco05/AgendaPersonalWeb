import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.modules.anotaciones.models import Note, Tag


@pytest.mark.asyncio
async def test_create_note(auth_client, db_session):
    response = await auth_client.post("/anotaciones/nueva", data={
        "title": "Mi primera nota",
        "content": "Contenido de prueba",
        "color": "#fef3c7",
    })
    assert response.status_code == 303
    assert response.headers["location"] == "/finanzas/"

    result = await db_session.execute(
        select(Note).where(Note.title == "Mi primera nota")
    )
    note = result.scalar_one_or_none()
    assert note is not None
    assert note.is_archived is False


@pytest.mark.asyncio
async def test_create_note_with_event_date(auth_client, db_session):
    response = await auth_client.post("/anotaciones/nueva", data={
        "title": "Nota con fecha",
        "content": "Contenido",
        "event_date": "2025-12-25",
    })
    assert response.status_code == 303

    result = await db_session.execute(
        select(Note).where(Note.title == "Nota con fecha")
    )
    note = result.scalar_one_or_none()
    assert note is not None
    assert note.event_date is not None


@pytest.mark.asyncio
async def test_list_notes(auth_client):
    response = await auth_client.get("/anotaciones/")
    assert response.status_code == 200
    assert "Notas" in response.text or "Mis Notas" in response.text


@pytest.mark.asyncio
async def test_list_notes_with_data(auth_client):
    await auth_client.post("/anotaciones/nueva", data={
        "title": "Nota visible",
        "content": "Contenido",
    })
    response = await auth_client.get("/anotaciones/")
    assert response.status_code == 200
    assert "Nota visible" in response.text


@pytest.mark.asyncio
async def test_edit_note(auth_client, db_session):
    await auth_client.post("/anotaciones/nueva", data={
        "title": "Original",
        "content": "Original content",
    })

    result = await db_session.execute(
        select(Note).where(Note.title == "Original")
    )
    note = result.scalar_one_or_none()
    assert note is not None

    response = await auth_client.post(f"/anotaciones/editar/{note.id}", data={
        "title": "Editada",
        "content": "Contenido editado",
        "color": "#dcfce7",
        "action": "save",
    })
    assert response.status_code == 303

    await db_session.refresh(note)
    assert note.title == "Editada"
    assert note.content == "Contenido editado"


@pytest.mark.asyncio
async def test_delete_note_via_edit(auth_client, db_session):
    await auth_client.post("/anotaciones/nueva", data={
        "title": "Para archivar",
        "content": "Contenido",
    })

    result = await db_session.execute(
        select(Note).where(Note.title == "Para archivar")
    )
    note = result.scalar_one_or_none()
    assert note is not None

    response = await auth_client.post(f"/anotaciones/editar/{note.id}", data={
        "title": "Para archivar",
        "content": "Contenido",
        "action": "delete",
    })
    assert response.status_code == 303

    await db_session.refresh(note)
    assert note.is_archived is True


@pytest.mark.asyncio
async def test_create_tag(auth_client, db_session):
    response = await auth_client.post("/anotaciones/etiquetas", data={
        "name": "Importante",
        "color": "#EF4444",
    })
    assert response.status_code == 303

    result = await db_session.execute(
        select(Tag).where(Tag.name == "Importante")
    )
    tag = result.scalar_one_or_none()
    assert tag is not None
    assert tag.color == "#EF4444"


@pytest.mark.asyncio
async def test_list_tags(auth_client):
    response = await auth_client.get("/anotaciones/etiquetas")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_note_with_tags(auth_client, db_session):
    tag_response = await auth_client.post("/anotaciones/etiquetas", data={
        "name": "Trabajo",
        "color": "#3B82F6",
    })
    assert tag_response.status_code == 303

    tag_result = await db_session.execute(
        select(Tag).where(Tag.name == "Trabajo")
    )
    tag = tag_result.scalar_one_or_none()
    assert tag is not None

    response = await auth_client.post("/anotaciones/nueva", data={
        "title": "Nota con tag",
        "content": "Contenido etiquetado",
        "tags": tag.id,
    })
    assert response.status_code == 303

    result = await db_session.execute(
        select(Note).options(selectinload(Note.tags)).where(Note.title == "Nota con tag")
    )
    note = result.scalar_one_or_none()
    assert note is not None
    tag_ids = [t.id for t in note.tags]
    assert tag.id in tag_ids


@pytest.mark.asyncio
async def test_delete_tag(auth_client, db_session):
    await auth_client.post("/anotaciones/etiquetas", data={
        "name": "Para eliminar",
        "color": "#94A3B8",
    })

    result = await db_session.execute(
        select(Tag).where(Tag.name == "Para eliminar")
    )
    tag = result.scalar_one_or_none()
    assert tag is not None

    response = await auth_client.post(f"/anotaciones/etiquetas/eliminar/{tag.id}")
    assert response.status_code == 303

    result = await db_session.execute(
        select(Tag).where(Tag.name == "Para eliminar")
    )
    tag = result.scalar_one_or_none()
    assert tag is None


@pytest.mark.asyncio
async def test_anotaciones_requires_auth(client):
    response = await client.get("/anotaciones/", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]

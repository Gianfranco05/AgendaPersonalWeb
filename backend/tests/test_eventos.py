import pytest
from sqlalchemy import select
from app.modules.eventos.models import Event


@pytest.mark.asyncio
async def test_create_event(auth_client, db_session):
    response = await auth_client.post("/eventos/nuevo", data={
        "title": "Reunion equipo",
        "description": "Weekly sync",
        "start_date": "2025-12-01",
        "start_time": "10:00",
        "color": "#3B82F6",
        "location": "Oficina",
    })
    assert response.status_code == 303
    assert response.headers["location"] == "/finanzas/"

    result = await db_session.execute(
        select(Event).where(Event.title == "Reunion equipo")
    )
    event = result.scalar_one_or_none()
    assert event is not None
    assert event.location == "Oficina"


@pytest.mark.asyncio
async def test_create_event_minimal(auth_client, db_session):
    response = await auth_client.post("/eventos/nuevo", data={
        "title": "Evento simple",
        "start_date": "2025-12-15",
    })
    assert response.status_code == 303

    result = await db_session.execute(
        select(Event).where(Event.title == "Evento simple")
    )
    event = result.scalar_one_or_none()
    assert event is not None


@pytest.mark.asyncio
async def test_list_events(auth_client):
    response = await auth_client.get("/eventos/")
    assert response.status_code == 200
    assert "Calendario" in response.text or "FullCalendar" in response.text


@pytest.mark.asyncio
async def test_list_events_with_data(auth_client):
    await auth_client.post("/eventos/nuevo", data={
        "title": "Evento calendario",
        "start_date": "2025-12-20",
    })
    response = await auth_client.get("/eventos/")
    assert response.status_code == 200
    assert "Evento calendario" in response.text


@pytest.mark.asyncio
async def test_edit_event(auth_client, db_session):
    await auth_client.post("/eventos/nuevo", data={
        "title": "Evento original",
        "start_date": "2025-12-01",
    })

    result = await db_session.execute(
        select(Event).where(Event.title == "Evento original")
    )
    event = result.scalar_one_or_none()
    assert event is not None

    response = await auth_client.post(f"/eventos/editar/{event.id}", data={
        "title": "Evento editado",
        "start_date": "2025-12-02",
        "start_time": "14:00",
        "action": "save",
    })
    assert response.status_code == 303

    await db_session.refresh(event)
    assert event.title == "Evento editado"


@pytest.mark.asyncio
async def test_delete_event(auth_client, db_session):
    await auth_client.post("/eventos/nuevo", data={
        "title": "Evento a borrar",
        "start_date": "2025-12-01",
    })

    result = await db_session.execute(
        select(Event).where(Event.title == "Evento a borrar")
    )
    event = result.scalar_one_or_none()
    assert event is not None

    response = await auth_client.post(f"/eventos/editar/{event.id}", data={
        "title": "Evento a borrar",
        "start_date": "2025-12-01",
        "action": "delete",
    })
    assert response.status_code == 303

    result = await db_session.execute(
        select(Event).where(Event.title == "Evento a borrar")
    )
    event = result.scalar_one_or_none()
    assert event is None


@pytest.mark.asyncio
async def test_new_event_form(auth_client):
    response = await auth_client.get("/eventos/nuevo")
    assert response.status_code == 200
    assert "Nuevo Evento" in response.text


@pytest.mark.asyncio
async def test_events_require_auth(client):
    response = await client.get("/eventos/", follow_redirects=False)
    assert response.status_code == 303
    assert "/auth/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_create_event_all_day(auth_client, db_session):
    response = await auth_client.post("/eventos/nuevo", data={
        "title": "Evento todo el dia",
        "start_date": "2025-12-25",
        "is_all_day": "true",
    })
    assert response.status_code == 303

    result = await db_session.execute(
        select(Event).where(Event.title == "Evento todo el dia")
    )
    event = result.scalar_one_or_none()
    assert event is not None
    assert event.is_all_day is True

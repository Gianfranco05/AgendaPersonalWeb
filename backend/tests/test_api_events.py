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


@pytest.mark.asyncio
async def test_api_events_crud_full(api_auth_client):
    create_resp = await api_auth_client.post("/api/v1/events", json={
        "title": "CRUD Event",
        "description": "CRUD desc",
        "start_datetime": "2025-07-10T09:00:00",
        "end_datetime": "2025-07-10T10:00:00",
        "color": "#ff0000",
    })
    assert create_resp.status_code == 201
    event = create_resp.json()
    event_id = event["id"]
    assert event["title"] == "CRUD Event"

    list_resp = await api_auth_client.get(
        "/api/v1/events?date_from=2025-07-01&date_to=2025-07-31"
    )
    assert list_resp.status_code == 200
    assert any(e["id"] == event_id for e in list_resp.json())

    update_resp = await api_auth_client.put(f"/api/v1/events/{event_id}", json={
        "title": "Updated Event",
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Updated Event"

    delete_resp = await api_auth_client.delete(f"/api/v1/events/{event_id}")
    assert delete_resp.status_code == 204

    list_after = await api_auth_client.get("/api/v1/events")
    assert all(e["id"] != event_id for e in list_after.json())


@pytest.mark.asyncio
async def test_api_export_events_ics(api_auth_client):
    await api_auth_client.post("/api/v1/events", json={
        "title": "Evento exportable",
        "description": "Descripcion, con coma",
        "start_datetime": "2025-07-01T10:00:00",
        "end_datetime": "2025-07-01T11:00:00",
        "location": "Oficina",
    })

    response = await api_auth_client.get("/api/v1/events/export/ics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/calendar")
    assert "eventos.ics" in response.headers["content-disposition"]
    body = response.text
    assert body.startswith("BEGIN:VCALENDAR")
    assert "SUMMARY:Evento exportable" in body
    assert "LOCATION:Oficina" in body
    assert body.endswith("END:VCALENDAR\r\n")


@pytest.mark.asyncio
async def test_api_export_events_ics_requires_auth(client):
    response = await client.get("/api/v1/events/export/ics")
    assert response.status_code == 401


# ── Hora de pared: lo que el cliente manda es lo que vuelve ────────────────

@pytest.mark.asyncio
async def test_evento_devuelve_la_misma_hora_de_pared_sin_offset(api_auth_client):
    created = await api_auth_client.post("/api/v1/events", json={
        "title": "Cena",
        "start_datetime": "2026-10-07T21:30:00",
        "end_datetime": "2026-10-07T23:00:00",
    })
    assert created.status_code == 201
    # Sin "Z" ni offset: web y mobile hacen new Date(valor) y lo toman como
    # hora local. Con "Z" (lo que daba Postgres) el evento se corria 3 horas.
    assert created.json()["start_datetime"] == "2026-10-07T21:30:00"
    assert created.json()["end_datetime"] == "2026-10-07T23:00:00"

    listed = await api_auth_client.get("/api/v1/events")
    assert listed.json()[0]["start_datetime"] == "2026-10-07T21:30:00"


def test_el_valor_guardado_es_aware_en_utc_sin_depender_de_la_zona_del_servidor():
    from datetime import timezone

    from app.modules.eventos.schemas import EventCreate, EventUpdate

    ev = EventCreate(title="x", start_datetime="2026-10-07T10:00:00")
    assert ev.start_datetime.tzinfo == timezone.utc
    assert ev.start_datetime.hour == 10

    # Un cliente que mande offset explicito se normaliza a UTC.
    ev = EventCreate(title="x", start_datetime="2026-10-07T10:00:00-03:00")
    assert (ev.start_datetime.hour, ev.start_datetime.tzinfo) == (13, timezone.utc)

    assert EventUpdate(start_datetime="2026-10-07T10:00:00").start_datetime.tzinfo == timezone.utc


def test_end_after_start_no_revienta_con_naive_y_aware_mezclados():
    from app.modules.eventos.schemas import EventCreate

    with pytest.raises(ValueError):
        EventCreate(
            title="x",
            start_datetime="2026-10-07T10:00:00",
            end_datetime="2026-10-07T09:00:00-00:00",
        )


@pytest.mark.asyncio
async def test_ics_exporta_hora_flotante_sin_z(api_auth_client):
    await api_auth_client.post("/api/v1/events", json={
        "title": "Cena", "start_datetime": "2026-10-07T21:30:00",
    })
    response = await api_auth_client.get("/api/v1/events/export/ics")
    assert "DTSTART:20261007T213000\r\n" in response.text

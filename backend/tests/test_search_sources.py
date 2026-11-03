"""Cobertura de tipos del buscador: cada fuente se encuentra por titulo y por contenido."""
from datetime import date

import pytest

from app.modules.biblioteca.models import Book
from app.modules.estudio.models import Exam, Subject
from app.modules.finanzas.models import Transaction
from app.modules.inversiones.models import Investment
from app.modules.metas.models import Goal
from app.modules.peliculas.models import MediaItem
from app.modules.proyectos.models import Project, ProjectTask
from app.modules.trabajo.models import WorkOpportunity
from app.modules.vehiculo.models import MaintenanceRecord, Vehicle
from app.modules.viajes.models import PackingItem, Trip
from tests.search_helpers import add, event, group, note, search_url, task, txn

pytestmark = pytest.mark.asyncio


def _investment(uid, title=None, content=None, **kw):
    return Investment(
        user_id=uid, asset_type="plazo_fijo", name=title or "X", currency="ARS",
        invested_amount=1000, notes=content, **kw,
    )


# (type, entity, factory(uid, title, content) -> lista de filas, hay campo de contenido)
# `parent` devuelve [padre, hijo]: el hijo es el ultimo.
CASES = {
    "note": ("notes", lambda u, t, c: [note(u, t or "x", c or "")]),
    "task": ("tasks", lambda u, t, c: [task(u, t or "x", c)]),
    "event": ("events", lambda u, t, c: [event(u, t or "x", description=c)]),
    "transaction": ("transactions", lambda u, t, c: [txn(u, t or "x", notes=c)]),
    "habit": ("habits", lambda u, t, c: [Goal(user_id=u, title=t or "x", goal_type="binary", description=c)]),
    "goal": ("goals", lambda u, t, c: [Goal(user_id=u, title=t or "x", goal_type="progress", description=c)]),
    "investment": ("investments", lambda u, t, c: [_investment(u, t, c)]),
    "subject": ("study", lambda u, t, c: [Subject(user_id=u, name=t or "x", professor=c)]),
    "book": ("library", lambda u, t, c: [Book(user_id=u, title=t or "x", author=c)]),
    "media_item": ("media", lambda u, t, c: [MediaItem(user_id=u, title=t or "x", notes=c)]),
    "opportunity": ("work", lambda u, t, c: [WorkOpportunity(user_id=u, role=t or "x", company=c or "ACME")]),
    "trip": ("travel", lambda u, t, c: [Trip(user_id=u, destination=t or "x", notes=c)]),
    "vehicle": ("vehicle", lambda u, t, c: [Vehicle(user_id=u, name=t or "x", brand=c)]),
    "project": ("projects", lambda u, t, c: [Project(user_id=u, name=t or "x", description=c)]),
}


@pytest.mark.parametrize("entity", list(CASES))
async def test_each_source_is_found_by_title(api_auth_client, db_session, test_user, entity):
    type_, factory = CASES[entity]
    rows = factory(test_user.id, "Zanahoria dorada", None)
    await add(db_session, *rows)
    resp = await api_auth_client.get(search_url("zanahoria"))
    g = group(resp.json(), type_)
    assert g is not None, resp.json()
    assert [i["id"] for i in g["items"]] == [rows[-1].id]
    assert g["items"][0]["entity"] == entity


@pytest.mark.parametrize("entity", list(CASES))
async def test_each_source_is_found_by_a_content_field(api_auth_client, db_session, test_user, entity):
    type_, factory = CASES[entity]
    rows = factory(test_user.id, "Titulo cualquiera", "Zapallito relleno")
    await add(db_session, *rows)
    resp = await api_auth_client.get(search_url("zapallito"))
    g = group(resp.json(), type_)
    assert g is not None, resp.json()
    item = g["items"][0]
    assert item["id"] == rows[-1].id
    assert item["title_highlights"] == [] or entity == "opportunity"


async def test_work_title_is_role_dot_company(api_auth_client, db_session, test_user):
    await add(db_session, WorkOpportunity(user_id=test_user.id, role="Backend Dev", company="Acme"))
    item = group((await api_auth_client.get(search_url("acme"))).json(), "work")["items"][0]
    assert item["title"] == "Backend Dev · Acme"
    assert item["title_highlights"] == [[14, 18]]


async def test_exam_has_parent_and_path(api_auth_client, db_session, test_user):
    s = Subject(user_id=test_user.id, name="Algebra")
    e = Exam(user_id=test_user.id, subject_id="", title="Parcial final", exam_date=date(2026, 11, 2), notes=None)
    await add(db_session, s)
    e.subject_id = s.id
    await add(db_session, e)
    item = group((await api_auth_client.get(search_url("parcial"))).json(), "study")["items"][0]
    assert item["entity"] == "exam"
    assert item["parent_id"] == s.id
    assert item["path"] == f"/study?open={e.id}&entity=exam&parent={s.id}"
    assert item["date"] == "2026-11-02"


async def test_study_group_mixes_subjects_and_exams(api_auth_client, db_session, test_user):
    s = await add(db_session, Subject(user_id=test_user.id, name="Analisis matematico"))
    await add(db_session, Exam(user_id=test_user.id, subject_id=s.id, title="Analisis: parcial", exam_date=date(2026, 12, 1)))
    g = group((await api_auth_client.get(search_url("analisis"))).json(), "study")
    assert {i["entity"] for i in g["items"]} == {"subject", "exam"}


async def test_packing_item_child_of_trip(api_auth_client, db_session, test_user):
    trip = await add(db_session, Trip(user_id=test_user.id, destination="Bariloche"))
    p = await add(db_session, PackingItem(user_id=test_user.id, trip_id=trip.id, name="Cargador"))
    item = group((await api_auth_client.get(search_url("cargador"))).json(), "travel")["items"][0]
    assert item["entity"] == "packing_item"
    assert item["parent_id"] == trip.id
    assert item["path"] == f"/travel?open={p.id}&entity=packing_item&parent={trip.id}"


async def test_maintenance_shows_type_and_vehicle_name(api_auth_client, db_session, test_user):
    v = await add(db_session, Vehicle(user_id=test_user.id, name="Gol Trend"))
    m = await add(
        db_session,
        MaintenanceRecord(
            user_id=test_user.id, vehicle_id=v.id, record_type="revision",
            record_date=date(2026, 9, 1), notes="Cambio de pastillas",
        ),
    )
    item = group((await api_auth_client.get(search_url("pastillas"))).json(), "vehicle")["items"][0]
    assert item["entity"] == "maintenance"
    assert item["title"] == "Revision · Gol Trend"
    assert item["snippet"] == "Cambio de pastillas"
    assert item["parent_id"] == v.id
    assert item["path"] == f"/vehicle?open={m.id}&entity=maintenance&parent={v.id}"


async def test_project_task_child_of_project(api_auth_client, db_session, test_user):
    p = await add(db_session, Project(user_id=test_user.id, name="Web nueva"))
    t = await add(db_session, ProjectTask(user_id=test_user.id, project_id=p.id, title="Disenar logo"))
    item = group((await api_auth_client.get(search_url("logo"))).json(), "projects")["items"][0]
    assert item["entity"] == "project_task"
    assert item["parent_id"] == p.id
    assert item["path"] == f"/projects?open={t.id}&entity=project_task&parent={p.id}"


async def test_deleted_transaction_is_not_returned(api_auth_client, db_session, test_user):
    await add(db_session, txn(test_user.id, "Nafta YPF", is_deleted=True), txn(test_user.id, "Nafta Shell"))
    items = group((await api_auth_client.get(search_url("nafta"))).json(), "transactions")["items"]
    assert [i["title"] for i in items] == ["Nafta Shell"]


async def test_habit_and_goal_go_to_different_groups(api_auth_client, db_session, test_user):
    await add(
        db_session,
        Goal(user_id=test_user.id, title="Leer 20 minutos", goal_type="binary"),
        Goal(user_id=test_user.id, title="Leer 12 libros", goal_type="progress"),
        Goal(user_id=test_user.id, title="Leer en voz alta", goal_type="metric"),
        Goal(user_id=test_user.id, title="Ahorro para leer", goal_type="savings"),
    )
    body = (await api_auth_client.get(search_url("leer"))).json()
    assert sorted(i["title"] for i in group(body, "habits")["items"]) == ["Leer 20 minutos", "Leer en voz alta"]
    assert sorted(i["title"] for i in group(body, "goals")["items"]) == ["Ahorro para leer", "Leer 12 libros"]
    assert [g["type"] for g in body["groups"]] == ["habits", "goals"]


async def test_transaction_meta_and_path(api_auth_client, db_session, test_user):
    t = await add(db_session, txn(test_user.id, "Super", amount=1234.5, type="income", currency="USD"))
    item = group((await api_auth_client.get(search_url("super"))).json(), "transactions")["items"][0]
    assert item["meta"] == {"amount": "1234.50", "currency": "USD", "type": "income"}
    assert item["path"] == f"/finances?tab=transacciones&open={t.id}"
    assert item["date"] == "2026-10-10"


async def test_investment_path_and_meta(api_auth_client, db_session, test_user):
    i = await add(db_session, _investment(test_user.id, "Plazo fijo Galicia", None))
    item = group((await api_auth_client.get(search_url("galicia"))).json(), "investments")["items"][0]
    assert item["path"] == f"/finances?tab=inversiones&open={i.id}"
    assert item["meta"]["asset_type"] == "plazo_fijo"


async def test_event_date_is_wall_clock_without_zone(api_auth_client, db_session, test_user):
    await add(db_session, event(test_user.id, "Cena"))
    item = group((await api_auth_client.get(search_url("cena"))).json(), "events")["items"][0]
    assert item["date"] == "2026-10-20T10:00:00"


async def test_ids_in_path_are_url_encoded(api_auth_client, db_session, test_user):
    n = note(test_user.id, "Algo raro")
    n.id = "a b&c=d/é"
    await add(db_session, n)
    item = group((await api_auth_client.get(search_url("raro"))).json(), "notes")["items"][0]
    assert item["path"] == "/notes?open=a%20b%26c%3Dd%2F%C3%A9"

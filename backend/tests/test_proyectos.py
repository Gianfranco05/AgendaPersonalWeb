import pytest
import pytest_asyncio

from app.modules.modulos.service import ModulesService

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def owns_projects(db_session, test_user):
    """La plantilla se compra antes de cada test: sin esto todo daria 402."""
    await ModulesService(db_session).grant(test_user.id, "projects")


async def _crear_proyecto(client, name="Rediseño web", **extra):
    resp = await client.post("/api/v1/projects", json={"name": name, **extra})
    assert resp.status_code == 201
    return resp.json()


async def _crear_tarea(client, project_id, title="Wireframes", **extra):
    resp = await client.post(
        "/api/v1/projects/tasks", json={"project_id": project_id, "title": title, **extra}
    )
    assert resp.status_code == 201
    return resp.json()


# ── Gate de compra ───────────────────────────────────────────────────────────

async def test_projects_endpoints_require_auth(client):
    assert (await client.get("/api/v1/projects")).status_code == 401


async def test_projects_endpoints_are_blocked_without_the_purchase(
    api_auth_client, db_session, test_user, monkeypatch
):
    from app.config import settings
    from app.modules.modulos.models import ModulePurchase
    from sqlalchemy import delete

    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")
    await db_session.execute(
        delete(ModulePurchase).where(
            ModulePurchase.user_id == test_user.id, ModulePurchase.module_key == "projects"
        )
    )
    await db_session.commit()

    resp = await api_auth_client.get("/api/v1/projects")
    assert resp.status_code == 402


# ── Proyectos ────────────────────────────────────────────────────────────────

async def test_create_and_list_projects(api_auth_client):
    await _crear_proyecto(api_auth_client, "Rediseño web")
    await _crear_proyecto(api_auth_client, "App mobile")

    proyectos = (await api_auth_client.get("/api/v1/projects")).json()
    assert {p["name"] for p in proyectos} == {"Rediseño web", "App mobile"}
    assert all(p["status"] == "activo" for p in proyectos)  # default


async def test_create_rejects_an_invalid_status(api_auth_client):
    resp = await api_auth_client.post(
        "/api/v1/projects", json={"name": "X", "status": "inventado"}
    )
    assert resp.status_code == 422


async def test_update_and_delete_project(api_auth_client):
    proyecto = await _crear_proyecto(api_auth_client)
    resp = await api_auth_client.patch(
        f"/api/v1/projects/{proyecto['id']}", json={"status": "pausado"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pausado"

    assert (await api_auth_client.delete(f"/api/v1/projects/{proyecto['id']}")).status_code == 204
    assert (await api_auth_client.get("/api/v1/projects")).json() == []


async def test_update_unknown_project_is_404(api_auth_client):
    resp = await api_auth_client.patch("/api/v1/projects/nope", json={"name": "X"})
    assert resp.status_code == 404


# ── Tablero (tareas) ─────────────────────────────────────────────────────────

async def test_create_task_for_an_unknown_project_is_404(api_auth_client):
    resp = await api_auth_client.post(
        "/api/v1/projects/tasks", json={"project_id": "no-existe", "title": "X"}
    )
    assert resp.status_code == 404


async def test_create_task_rejects_an_invalid_status(api_auth_client):
    proyecto = await _crear_proyecto(api_auth_client)
    resp = await api_auth_client.post(
        "/api/v1/projects/tasks",
        json={"project_id": proyecto["id"], "title": "X", "status": "inventado"},
    )
    assert resp.status_code == 422


async def test_create_and_move_task_across_the_board(api_auth_client):
    proyecto = await _crear_proyecto(api_auth_client)
    tarea = await _crear_tarea(api_auth_client, proyecto["id"])
    assert tarea["status"] == "pendiente"  # default

    resp = await api_auth_client.patch(
        f"/api/v1/projects/tasks/{tarea['id']}", json={"status": "en_progreso"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "en_progreso"


async def test_list_tasks_filtered_by_project(api_auth_client):
    p1 = await _crear_proyecto(api_auth_client, "P1")
    p2 = await _crear_proyecto(api_auth_client, "P2")
    t1 = await _crear_tarea(api_auth_client, p1["id"], "T1")
    await _crear_tarea(api_auth_client, p2["id"], "T2")

    resp = await api_auth_client.get("/api/v1/projects/tasks", params={"project_id": p1["id"]})
    assert [t["id"] for t in resp.json()] == [t1["id"]]


async def test_cannot_add_a_task_to_another_users_project(api_auth_client, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User
    from app.modules.proyectos.service import ProjectsService

    otro = User(
        email="otro_proj@test.com",
        password_hash=hash_password("test123"),
        full_name="Otro",
        is_active=True,
    )
    db_session.add(otro)
    await db_session.commit()
    proyecto_ajeno = await ProjectsService(db_session).create_project(otro.id, "Ajeno")

    resp = await api_auth_client.post(
        "/api/v1/projects/tasks", json={"project_id": proyecto_ajeno.id, "title": "Colada"}
    )
    assert resp.status_code == 404


async def test_deleting_a_project_also_deletes_its_tasks(api_auth_client, db_session):
    proyecto = await _crear_proyecto(api_auth_client)
    await _crear_tarea(api_auth_client, proyecto["id"])

    assert (await api_auth_client.delete(f"/api/v1/projects/{proyecto['id']}")).status_code == 204

    from sqlalchemy import select
    from app.modules.proyectos.models import ProjectTask

    restantes = (await db_session.execute(select(ProjectTask))).scalars().all()
    assert list(restantes) == []


async def test_delete_task(api_auth_client):
    proyecto = await _crear_proyecto(api_auth_client)
    tarea = await _crear_tarea(api_auth_client, proyecto["id"])
    assert (await api_auth_client.delete(f"/api/v1/projects/tasks/{tarea['id']}")).status_code == 204
    assert (await api_auth_client.get("/api/v1/projects/tasks")).json() == []


# ── Resumen ──────────────────────────────────────────────────────────────────

async def test_summary_counts_projects_and_tasks(api_auth_client):
    p1 = await _crear_proyecto(api_auth_client, "P1", status="activo")
    await _crear_proyecto(api_auth_client, "P2", status="completado")
    await _crear_tarea(api_auth_client, p1["id"], "T1", status="pendiente")
    await _crear_tarea(api_auth_client, p1["id"], "T2", status="en_progreso")
    await _crear_tarea(api_auth_client, p1["id"], "T3", status="hecho")

    data = (await api_auth_client.get("/api/v1/projects/summary")).json()
    assert data["projects_total"] == 2
    assert data["projects_active"] == 1
    assert data["tasks_pending"] == 1
    assert data["tasks_in_progress"] == 1
    assert data["tasks_done"] == 1


async def test_summary_without_data(api_auth_client):
    data = (await api_auth_client.get("/api/v1/projects/summary")).json()
    assert data["projects_total"] == 0
    assert data["tasks_pending"] == 0

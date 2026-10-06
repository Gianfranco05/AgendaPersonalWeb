from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.modules.estudio.models import Exam

pytestmark = pytest.mark.asyncio


async def _crear_materia(client, name="Análisis Matemático", **extra):
    resp = await client.post("/api/v1/study/subjects", json={"name": name, **extra})
    assert resp.status_code == 201
    return resp.json()


async def _crear_examen(client, subject_id, title="Primer parcial", days=7, **extra):
    resp = await client.post(
        "/api/v1/study/exams",
        json={
            "subject_id": subject_id,
            "title": title,
            "exam_date": (date.today() + timedelta(days=days)).isoformat(),
            **extra,
        },
    )
    assert resp.status_code == 201
    return resp.json()


# ── Auth ─────────────────────────────────────────────────────────────────────

async def test_study_endpoints_require_auth(client):
    assert (await client.get("/api/v1/study/subjects")).status_code == 401
    assert (await client.get("/api/v1/study/exams")).status_code == 401
    assert (await client.get("/api/v1/study/summary")).status_code == 401


# ── Materias ─────────────────────────────────────────────────────────────────

async def test_create_and_list_subjects(api_auth_client):
    await _crear_materia(api_auth_client, "Álgebra")
    await _crear_materia(api_auth_client, "Física")

    materias = (await api_auth_client.get("/api/v1/study/subjects")).json()
    assert [m["name"] for m in materias] == ["Álgebra", "Física"]  # ordenadas por nombre
    assert materias[0]["status"] == "cursando"  # default


async def test_create_subject_rejects_an_invalid_status(api_auth_client):
    resp = await api_auth_client.post(
        "/api/v1/study/subjects", json={"name": "X", "status": "inventado"}
    )
    assert resp.status_code == 422


async def test_update_subject(api_auth_client):
    materia = await _crear_materia(api_auth_client)

    resp = await api_auth_client.patch(
        f"/api/v1/study/subjects/{materia['id']}",
        json={"status": "aprobada", "professor": "Gauss"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "aprobada"
    assert resp.json()["professor"] == "Gauss"


async def test_update_unknown_subject_is_404(api_auth_client):
    resp = await api_auth_client.patch("/api/v1/study/subjects/nope", json={"name": "X"})
    assert resp.status_code == 404


async def test_deleting_a_subject_also_deletes_its_exams(
    api_auth_client, db_session
):
    materia = await _crear_materia(api_auth_client)
    await _crear_examen(api_auth_client, materia["id"])

    resp = await api_auth_client.delete(f"/api/v1/study/subjects/{materia['id']}")
    assert resp.status_code == 204

    # Sin esto quedarian examenes apuntando a una materia que ya no existe.
    restantes = (await db_session.execute(select(Exam))).scalars().all()
    assert list(restantes) == []


# ── Examenes ─────────────────────────────────────────────────────────────────

async def test_create_exam(api_auth_client):
    materia = await _crear_materia(api_auth_client)
    examen = await _crear_examen(api_auth_client, materia["id"], grade=8.5)

    assert examen["grade"] == 8.5
    assert examen["subject_id"] == materia["id"]


async def test_exam_grade_out_of_range_is_rejected(api_auth_client):
    materia = await _crear_materia(api_auth_client)
    resp = await api_auth_client.post(
        "/api/v1/study/exams",
        json={
            "subject_id": materia["id"],
            "title": "Final",
            "exam_date": date.today().isoformat(),
            "grade": 42,
        },
    )
    assert resp.status_code == 422


async def test_exam_for_an_unknown_subject_is_404(api_auth_client):
    resp = await api_auth_client.post(
        "/api/v1/study/exams",
        json={
            "subject_id": "no-existe",
            "title": "Final",
            "exam_date": date.today().isoformat(),
        },
    )
    assert resp.status_code == 404


async def test_upcoming_filter_excludes_past_exams(api_auth_client):
    materia = await _crear_materia(api_auth_client)
    await _crear_examen(api_auth_client, materia["id"], "Viejo", days=-10)
    await _crear_examen(api_auth_client, materia["id"], "Próximo", days=5)

    todos = (await api_auth_client.get("/api/v1/study/exams")).json()
    assert len(todos) == 2

    proximos = (
        await api_auth_client.get("/api/v1/study/exams", params={"upcoming": True})
    ).json()
    assert [e["title"] for e in proximos] == ["Próximo"]


async def test_update_and_delete_exam(api_auth_client):
    materia = await _crear_materia(api_auth_client)
    examen = await _crear_examen(api_auth_client, materia["id"])

    resp = await api_auth_client.patch(
        f"/api/v1/study/exams/{examen['id']}", json={"grade": 9}
    )
    assert resp.status_code == 200
    assert resp.json()["grade"] == 9

    assert (await api_auth_client.delete(f"/api/v1/study/exams/{examen['id']}")).status_code == 204
    assert (await api_auth_client.get("/api/v1/study/exams")).json() == []


# ── Resumen ──────────────────────────────────────────────────────────────────

async def test_summary_counts_and_averages(api_auth_client):
    cursando = await _crear_materia(api_auth_client, "Álgebra")
    await _crear_materia(api_auth_client, "Física", status="aprobada")

    await _crear_examen(api_auth_client, cursando["id"], "Parcial 1", days=-5, grade=8)
    await _crear_examen(api_auth_client, cursando["id"], "Parcial 2", days=-2, grade=6)
    await _crear_examen(api_auth_client, cursando["id"], "Final", days=10)

    data = (await api_auth_client.get("/api/v1/study/summary")).json()
    assert data["subjects_total"] == 2
    assert data["subjects_cursando"] == 1
    assert data["subjects_aprobadas"] == 1
    assert data["average_grade"] == 7  # (8 + 6) / 2, ignora el examen sin nota
    assert data["upcoming_count"] == 1
    assert data["next_exam"]["title"] == "Final"


async def test_summary_without_data(api_auth_client):
    data = (await api_auth_client.get("/api/v1/study/summary")).json()
    assert data["subjects_total"] == 0
    assert data["average_grade"] is None
    assert data["next_exam"] is None


# ── Aislamiento entre usuarios ───────────────────────────────────────────────

async def test_subjects_and_exams_of_another_user_are_not_reachable(
    api_auth_client, db_session
):
    from app.core.security import hash_password
    from app.modules.auth.models import User
    from app.modules.estudio.service import StudyService

    otro = User(
        email="otro_estudio@test.com",
        password_hash=hash_password("test123"),
        full_name="Otro",
        is_active=True,
    )
    db_session.add(otro)
    await db_session.commit()

    materia_ajena = await StudyService(db_session).create_subject(otro.id, "Ajena")
    examen_ajeno = await StudyService(db_session).create_exam(
        otro.id, materia_ajena.id, "Parcial ajeno", date.today()
    )

    assert (await api_auth_client.get("/api/v1/study/subjects")).json() == []
    assert (await api_auth_client.get("/api/v1/study/exams")).json() == []
    assert (
        await api_auth_client.patch(
            f"/api/v1/study/subjects/{materia_ajena.id}", json={"name": "Hackeada"}
        )
    ).status_code == 404
    assert (
        await api_auth_client.delete(f"/api/v1/study/exams/{examen_ajeno.id}")
    ).status_code == 404


async def test_cannot_attach_an_exam_to_another_users_subject(api_auth_client, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User
    from app.modules.estudio.service import StudyService

    otro = User(
        email="otro_estudio2@test.com",
        password_hash=hash_password("test123"),
        full_name="Otro",
        is_active=True,
    )
    db_session.add(otro)
    await db_session.commit()
    materia_ajena = await StudyService(db_session).create_subject(otro.id, "Ajena")

    resp = await api_auth_client.post(
        "/api/v1/study/exams",
        json={
            "subject_id": materia_ajena.id,
            "title": "Colado",
            "exam_date": date.today().isoformat(),
        },
    )
    assert resp.status_code == 404


def test_local_today_respeta_el_huso_del_cliente(monkeypatch):
    from datetime import date, datetime, timezone

    from app.core import clock

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            # 23:30 UTC del 6/10 == 20:30 del 6/10 en Buenos Aires...
            return datetime(2026, 10, 7, 0, 30, tzinfo=timezone.utc)

    monkeypatch.setattr(clock, "datetime", FakeDatetime)
    # ...y a las 00:30 UTC del 7/10 todavia es 6/10 en Argentina (UTC-3).
    assert clock.local_today(-180) == date(2026, 10, 6)
    assert clock.local_today(0) == date(2026, 10, 7)

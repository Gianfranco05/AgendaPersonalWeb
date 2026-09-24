import pytest
import pytest_asyncio

from app.modules.modulos.service import ModulesService

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def owns_library(db_session, test_user):
    """La plantilla se compra antes de cada test: sin esto todo daria 402."""
    await ModulesService(db_session).grant(test_user.id, "library")


async def _crear_libro(client, title="Rayuela", **extra):
    resp = await client.post("/api/v1/library/books", json={"title": title, **extra})
    assert resp.status_code == 201
    return resp.json()


# ── Gate de compra ───────────────────────────────────────────────────────────

async def test_library_endpoints_require_auth(client):
    assert (await client.get("/api/v1/library/books")).status_code == 401


async def test_library_endpoints_are_blocked_without_the_purchase(
    api_auth_client, db_session, test_user, monkeypatch
):
    """Confirma que este router esta enganchado a require_module("library") y
    no, por copy-paste, a otra plantilla.
    """
    from app.config import settings
    from app.modules.modulos.models import ModulePurchase
    from sqlalchemy import delete

    monkeypatch.setattr(settings, "BILLING_PROVIDER", "stripe")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")
    # El fixture de arriba ya compro "library" para este usuario; se revierte
    # solo eso, sin tocar el resto de la fixture.
    await db_session.execute(
        delete(ModulePurchase).where(
            ModulePurchase.user_id == test_user.id, ModulePurchase.module_key == "library"
        )
    )
    await db_session.commit()

    resp = await api_auth_client.get("/api/v1/library/books")
    assert resp.status_code == 402


# ── CRUD ─────────────────────────────────────────────────────────────────────

async def test_create_and_list_books(api_auth_client):
    await _crear_libro(api_auth_client, "Rayuela", author="Cortázar")
    await _crear_libro(api_auth_client, "1984", author="Orwell")

    libros = (await api_auth_client.get("/api/v1/library/books")).json()
    assert {b["title"] for b in libros} == {"Rayuela", "1984"}
    assert all(b["status"] == "pendiente" for b in libros)  # default


async def test_create_book_rejects_an_invalid_status(api_auth_client):
    resp = await api_auth_client.post(
        "/api/v1/library/books", json={"title": "X", "status": "inventado"}
    )
    assert resp.status_code == 422


async def test_rating_out_of_range_is_rejected(api_auth_client):
    resp = await api_auth_client.post(
        "/api/v1/library/books", json={"title": "X", "rating": 7}
    )
    assert resp.status_code == 422


async def test_update_book(api_auth_client):
    libro = await _crear_libro(api_auth_client)
    resp = await api_auth_client.patch(
        f"/api/v1/library/books/{libro['id']}",
        json={"status": "leido", "rating": 4.5, "finished_date": "2026-08-01"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "leido"
    assert resp.json()["rating"] == 4.5


async def test_update_unknown_book_is_404(api_auth_client):
    resp = await api_auth_client.patch("/api/v1/library/books/nope", json={"title": "X"})
    assert resp.status_code == 404


async def test_update_with_explicit_null_clears_the_field(api_auth_client):
    """Regresion: un PATCH con `author: null` debe borrar el autor, no ignorarlo.

    `changes` ya viene filtrado por `exclude_unset=True` en el router, asi que
    si el campo aparece es porque el cliente lo mando de verdad — incluido un
    `None` explicito para borrar un campo opcional.
    """
    libro = await _crear_libro(api_auth_client, author="Cortázar")
    assert libro["author"] == "Cortázar"

    resp = await api_auth_client.patch(
        f"/api/v1/library/books/{libro['id']}", json={"author": None}
    )
    assert resp.status_code == 200
    assert resp.json()["author"] is None


async def test_delete_book(api_auth_client):
    libro = await _crear_libro(api_auth_client)
    assert (await api_auth_client.delete(f"/api/v1/library/books/{libro['id']}")).status_code == 204
    assert (await api_auth_client.get("/api/v1/library/books")).json() == []


async def test_filter_by_status(api_auth_client):
    await _crear_libro(api_auth_client, "Pendiente")
    leido = await _crear_libro(api_auth_client, "Leido", status="leido")

    resp = await api_auth_client.get("/api/v1/library/books", params={"status": "leido"})
    assert [b["id"] for b in resp.json()] == [leido["id"]]


async def test_filter_by_invalid_status_is_rejected(api_auth_client):
    resp = await api_auth_client.get("/api/v1/library/books", params={"status": "bogus"})
    assert resp.status_code == 422


# ── Resumen ──────────────────────────────────────────────────────────────────

async def test_summary_averages_only_finished_books(api_auth_client):
    await _crear_libro(api_auth_client, "Uno", status="leido", rating=4)
    await _crear_libro(api_auth_client, "Dos", status="leido", rating=2)
    await _crear_libro(api_auth_client, "Tres", status="pendiente", rating=5)  # no cuenta

    data = (await api_auth_client.get("/api/v1/library/summary")).json()
    assert data["total"] == 3
    assert data["leidos"] == 2
    assert data["pendientes"] == 1
    assert data["average_rating"] == 3  # (4 + 2) / 2


async def test_summary_without_data(api_auth_client):
    data = (await api_auth_client.get("/api/v1/library/summary")).json()
    assert data["total"] == 0
    assert data["average_rating"] is None


# ── Aislamiento entre usuarios ───────────────────────────────────────────────

async def test_books_of_another_user_are_not_reachable(api_auth_client, db_session):
    from app.core.security import hash_password
    from app.modules.auth.models import User
    from app.modules.biblioteca.service import LibraryService

    otro = User(
        email="otro_lib@test.com",
        password_hash=hash_password("test123"),
        full_name="Otro",
        is_active=True,
    )
    db_session.add(otro)
    await db_session.commit()
    ajeno = await LibraryService(db_session).create_book(otro.id, "Ajeno")

    assert (await api_auth_client.get("/api/v1/library/books")).json() == []
    assert (
        await api_auth_client.patch(f"/api/v1/library/books/{ajeno.id}", json={"title": "Hackeado"})
    ).status_code == 404
    assert (await api_auth_client.delete(f"/api/v1/library/books/{ajeno.id}")).status_code == 404

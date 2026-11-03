"""Buscador global: GET /api/v1/search."""
import pytest

from tests.search_helpers import (
    add,
    event,
    group,
    make_other_user,
    note,
    search_url,
    tag_note,
    task,
    titles,
    txn,
    utc,
)

pytestmark = pytest.mark.asyncio


async def get(client, q, **params):
    return await client.get(search_url(q, **params))


# ── 3.1 Validacion ───────────────────────────────────────────────────────────


async def test_search_requires_a_session(client):
    resp = await client.get("/api/v1/search?q=ab")
    assert resp.status_code == 401


@pytest.mark.parametrize("q", ["a", " a ", "   "])
async def test_query_with_less_than_two_characters_is_422(api_auth_client, q):
    resp = await get(api_auth_client, q)
    assert resp.status_code == 422
    assert "al menos 2" in resp.text


async def test_missing_query_is_422(api_auth_client):
    assert (await api_auth_client.get("/api/v1/search")).status_code == 422


async def test_query_of_101_characters_is_422_and_100_is_ok(api_auth_client):
    assert (await get(api_auth_client, "a" * 101)).status_code == 422
    assert (await get(api_auth_client, "a" * 100)).status_code == 200


@pytest.mark.parametrize("limit", ["0", "21", "-1", "abc"])
async def test_limit_out_of_range_is_422(api_auth_client, limit):
    assert (await get(api_auth_client, "cafe", limit=limit)).status_code == 422


@pytest.mark.parametrize("limit", ["1", "20"])
async def test_limit_bounds_are_accepted(api_auth_client, limit):
    assert (await get(api_auth_client, "cafe", limit=limit)).status_code == 200


async def test_unknown_type_is_422_in_spanish(api_auth_client):
    resp = await get(api_auth_client, "cafe", types="notes,passwords")
    assert resp.status_code == 422
    assert "passwords" in resp.text


async def test_empty_types_means_all_and_known_types_are_accepted(api_auth_client):
    assert (await get(api_auth_client, "cafe", types="")).status_code == 200
    assert (await get(api_auth_client, "cafe", types="notes, tasks")).status_code == 200


async def test_no_matches_returns_200_with_no_groups(api_auth_client, db_session, test_user):
    await add(db_session, note(test_user.id, "Algo"))
    resp = await get(api_auth_client, "zzzzzz")
    assert resp.status_code == 200
    assert resp.json() == {"query": "zzzzzz", "groups": []}


async def test_response_echoes_the_normalized_query_and_is_not_cacheable(api_auth_client):
    resp = await get(api_auth_client, "  Café   con  ")
    assert resp.json()["query"] == "Café con"
    assert resp.headers["cache-control"] == "no-store"


# ── 3.2 Tildes y mayusculas ──────────────────────────────────────────────────


async def test_query_without_accent_finds_accented_data(api_auth_client, db_session, test_user):
    await add(db_session, note(test_user.id, "Café"))
    assert titles((await get(api_auth_client, "cafe")).json(), "notes") == ["Café"]


async def test_query_with_accent_finds_unaccented_data(api_auth_client, db_session, test_user):
    await add(db_session, task(test_user.id, "Llamar a Jose"))
    assert titles((await get(api_auth_client, "josé")).json(), "tasks") == ["Llamar a Jose"]


async def test_uppercase_accented_data_is_found_on_sqlite(api_auth_client, db_session, test_user):
    # lower() de SQLite no baja la "Ó": el plegado explicito lo cubre.
    await add(db_session, event(test_user.id, "REUNIÓN ANUAL"))
    assert titles((await get(api_auth_client, "reunion")).json(), "events") == ["REUNIÓN ANUAL"]


async def test_enie_folds_to_n_in_both_directions(api_auth_client, db_session, test_user):
    await add(db_session, note(test_user.id, "Cumple de la niña"), note(test_user.id, "Cuenta NINO"))
    assert titles((await get(api_auth_client, "nina")).json(), "notes") == ["Cumple de la niña"]
    assert titles((await get(api_auth_client, "niño")).json(), "notes") == ["Cuenta NINO"]
    assert titles((await get(api_auth_client, "NIÑA")).json(), "notes") == ["Cumple de la niña"]


async def test_partial_word_matches_merchant_of_a_transaction(api_auth_client, db_session, test_user):
    await add(db_session, txn(test_user.id, "Medialunas", merchant="Cafetería Central"))
    assert titles((await get(api_auth_client, "cafet")).json(), "transactions") == ["Medialunas"]


# ── 3.3 Tokens y comodines ───────────────────────────────────────────────────


async def test_all_tokens_must_match(api_auth_client, db_session, test_user):
    await add(db_session, note(test_user.id, "Café con Juan"), note(test_user.id, "Café solo"))
    assert titles((await get(api_auth_client, "cafe juan")).json(), "notes") == ["Café con Juan"]


async def test_tokens_may_match_different_fields(api_auth_client, db_session, test_user):
    await add(db_session, note(test_user.id, "Presupuesto", content="para el viaje a Salta"))
    assert titles((await get(api_auth_client, "viaje presupuesto")).json(), "notes") == ["Presupuesto"]


async def test_percent_is_literal(api_auth_client, db_session, test_user):
    await add(db_session, note(test_user.id, "Descuento 20%"), note(test_user.id, "Descuento 200"))
    assert titles((await get(api_auth_client, "20%")).json(), "notes") == ["Descuento 20%"]


async def test_underscore_is_literal(api_auth_client, db_session, test_user):
    await add(db_session, note(test_user.id, "mi_archivo"), note(test_user.id, "miXarchivo"))
    assert titles((await get(api_auth_client, "mi_a")).json(), "notes") == ["mi_archivo"]


async def test_only_wildcards_do_not_match_everything(api_auth_client, db_session, test_user):
    await add(db_session, note(test_user.id, "Hola"), note(test_user.id, "Sube 100%% fijo"))
    assert titles((await get(api_auth_client, "%%")).json(), "notes") == ["Sube 100%% fijo"]


async def test_backslash_is_literal_and_does_not_break_the_escape(api_auth_client, db_session, test_user):
    bs = chr(92)
    await add(db_session, note(test_user.id, f"ruta C:{bs}datos"), note(test_user.id, "ruta C:datos"))
    resp = await get(api_auth_client, f"C:{bs}datos")
    assert resp.status_code == 200
    assert titles(resp.json(), "notes") == [f"ruta C:{bs}datos"]


async def test_sql_metacharacters_never_cause_a_500(api_auth_client):
    for q in ["'; DROP TABLE notes;--", '" OR 1=1', "%_%_", "[a-z]", "a'b"]:
        assert (await get(api_auth_client, q)).status_code == 200


async def test_extra_tokens_beyond_five_are_ignored(api_auth_client, db_session, test_user):
    await add(db_session, note(test_user.id, "uno dos tres cuatro cinco"))
    resp = await get(api_auth_client, "uno dos tres cuatro cinco seis")
    assert titles(resp.json(), "notes") == ["uno dos tres cuatro cinco"]


# ── 3.4 Ranking ──────────────────────────────────────────────────────────────


async def test_title_match_beats_a_newer_content_match(api_auth_client, db_session, test_user):
    await add(
        db_session,
        note(test_user.id, "Presupuesto viaje", updated=utc(2026, 1, 1)),
        note(test_user.id, "Ideas", content="el presupuesto del mes", updated=utc(2026, 10, 1)),
    )
    assert titles((await get(api_auth_client, "presupuesto")).json(), "notes") == [
        "Presupuesto viaje",
        "Ideas",
    ]


async def test_prefix_beats_contains(api_auth_client, db_session, test_user):
    await add(
        db_session,
        task(test_user.id, "Recordar pagar luz"),
        task(test_user.id, "Pagar luz"),
    )
    assert titles((await get(api_auth_client, "pagar")).json(), "tasks") == [
        "Pagar luz",
        "Recordar pagar luz",
    ]


async def test_whole_query_prefix_is_rank_zero_even_with_accents(api_auth_client, db_session, test_user):
    await add(
        db_session,
        note(test_user.id, "El viaje a Córdoba y la comida", updated=utc(2026, 10, 1)),
        note(test_user.id, "Córdoba en familia", updated=utc(2026, 1, 1)),
    )
    assert titles((await get(api_auth_client, "cordoba")).json(), "notes") == [
        "Córdoba en familia",
        "El viaje a Córdoba y la comida",
    ]


async def test_most_recent_first_at_equal_rank(api_auth_client, db_session, test_user):
    await add(
        db_session,
        note(test_user.id, "Mi gym viejo", updated=utc(2026, 1, 1)),
        note(test_user.id, "Mi gym nuevo", updated=utc(2026, 10, 1)),
        note(test_user.id, "Mi gym medio", updated=utc(2026, 5, 1)),
    )
    assert titles((await get(api_auth_client, "gym")).json(), "notes") == [
        "Mi gym nuevo",
        "Mi gym medio",
        "Mi gym viejo",
    ]


async def test_limit_is_applied_after_ordering_and_sets_has_more(api_auth_client, db_session, test_user):
    rows = [note(test_user.id, f"Reunión {i}", updated=utc(2026, 1, i + 1)) for i in range(7)]
    rows.append(note(test_user.id, "Reunión importante", updated=utc(2026, 1, 1)))
    # todas son rank 1 salvo las que empiezan con la frase completa
    await add(db_session, *rows)
    resp = await get(api_auth_client, "reunion", types="notes", limit="5")
    g = group(resp.json(), "notes")
    assert len(g["items"]) == 5
    assert g["has_more"] is True
    # Todas empiezan con "reunion": rank 0 igual, entonces gana la mas reciente
    assert g["items"][0]["title"] == "Reunión 6"

    resp = await get(api_auth_client, "reunion", types="notes", limit="20")
    g = group(resp.json(), "notes")
    assert len(g["items"]) == 8 and g["has_more"] is False


async def test_has_more_is_false_when_exactly_limit_items(api_auth_client, db_session, test_user):
    await add(db_session, *[note(test_user.id, f"gym {i}") for i in range(3)])
    g = group((await get(api_auth_client, "gym", limit="3")).json(), "notes")
    assert len(g["items"]) == 3 and g["has_more"] is False


# ── 3.6 Forma de la respuesta ────────────────────────────────────────────────


async def test_item_shape_and_title_highlights(api_auth_client, db_session, test_user):
    n = await add(db_session, note(test_user.id, "Café con Juan", content="quedamos en el café de la esquina"))
    resp = await get(api_auth_client, "cafe")
    item = group(resp.json(), "notes")["items"][0]
    assert item["id"] == n.id
    assert item["type"] == "notes" and item["entity"] == "note"
    assert item["title"] == "Café con Juan"
    assert item["title_highlights"] == [[0, 4]]
    assert item["snippet"] == "quedamos en el café de la esquina"
    assert item["snippet_highlights"] == [[15, 19]]
    assert item["parent_id"] is None
    assert item["path"] == f"/notes?open={n.id}"
    assert item["meta"] == {"tags": [], "archived": False}
    assert item["date"].endswith("Z") and item["date"].startswith("20")


async def test_long_content_gets_a_window_with_ellipsis(api_auth_client, db_session, test_user):
    content = ("relleno de texto " * 100) + "factura de luz " + ("mas relleno " * 20)
    await add(db_session, note(test_user.id, "Papeles", content=content))
    item = group((await get(api_auth_client, "factura")).json(), "notes")["items"][0]
    assert item["snippet"].startswith("…") and item["snippet"].endswith("…")
    assert len(item["snippet"]) <= 145
    s, e = item["snippet_highlights"][0]
    assert item["snippet"][s:e] == "factura"
    assert item["title_highlights"] == []


async def test_stored_html_comes_back_as_literal_text(api_auth_client, db_session, test_user):
    await add(db_session, note(test_user.id, "<b>hola</b>", content="<img src=x onerror=alert(1)> hola"))
    item = group((await get(api_auth_client, "hola")).json(), "notes")["items"][0]
    assert item["title"] == "<b>hola</b>"
    assert item["title_highlights"] == [[3, 7]]
    assert item["snippet"] == "<img src=x onerror=alert(1)> hola"


async def test_groups_have_fixed_order_and_label_and_empty_ones_are_omitted(
    api_auth_client, db_session, test_user
):
    await add(
        db_session,
        txn(test_user.id, "Café molido"),
        task(test_user.id, "Comprar café"),
        note(test_user.id, "Café con Juan"),
        event(test_user.id, "Café de las 5"),
    )
    groups = (await get(api_auth_client, "cafe")).json()["groups"]
    assert [g["type"] for g in groups] == ["notes", "tasks", "events", "transactions"]
    assert [g["label"] for g in groups] == ["Notas", "Tareas", "Eventos", "Movimientos"]


async def test_archived_notes_are_included_and_marked(api_auth_client, db_session, test_user):
    await add(db_session, note(test_user.id, "Plan viejo", archived=True))
    item = group((await get(api_auth_client, "plan")).json(), "notes")["items"][0]
    assert item["meta"]["archived"] is True


async def test_note_found_by_tag_name_with_tags_in_meta(api_auth_client, db_session, test_user):
    n = await add(db_session, note(test_user.id, "Ideas", content="nada"))
    await tag_note(db_session, n, "Facultad", test_user.id)
    item = group((await get(api_auth_client, "facultad")).json(), "notes")["items"][0]
    assert item["title"] == "Ideas"
    assert item["meta"]["tags"] == ["Facultad"]
    assert item["title_highlights"] == []


# ── 3.7 Aislamiento ──────────────────────────────────────────────────────────


async def test_other_users_data_is_never_returned(api_auth_client, db_session, test_user):
    other = await make_other_user(db_session)
    await add(db_session, note(other.id, "Proyecto secreto"), task(other.id, "Secreto de tarea"))
    resp = await get(api_auth_client, "secreto")
    assert resp.json()["groups"] == []


async def test_other_users_tag_does_not_match_my_notes(api_auth_client, db_session, test_user):
    other = await make_other_user(db_session)
    theirs = await add(db_session, note(other.id, "Ideas de A"))
    await tag_note(db_session, theirs, "Secreto", other.id)
    await add(db_session, note(test_user.id, "Ideas"))
    assert (await get(api_auth_client, "secreto")).json()["groups"] == []


async def test_has_more_ignores_other_users_rows(api_auth_client, db_session, test_user):
    other = await make_other_user(db_session)
    await add(db_session, *[note(other.id, f"gym a{i}") for i in range(10)])
    await add(db_session, *[note(test_user.id, f"gym b{i}") for i in range(2)])
    g = group((await get(api_auth_client, "gym", types="notes", limit="5")).json(), "notes")
    assert len(g["items"]) == 2 and g["has_more"] is False


# ── 3.8 Plantillas pagas ─────────────────────────────────────────────────────


@pytest.fixture
def billing_on(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "BILLING_PROVIDER", "mercadopago")
    monkeypatch.setattr(settings, "MERCADOPAGO_ACCESS_TOKEN", "token-de-prueba")


async def _media(db, user_id, title="Dune"):
    from app.modules.peliculas.models import MediaItem

    return await add(db, MediaItem(user_id=user_id, title=title))


async def test_not_purchased_template_has_no_group_even_with_rows(
    api_auth_client, db_session, test_user, billing_on
):
    from app.modules.biblioteca.models import Book

    await add(db_session, Book(user_id=test_user.id, title="Dune"))
    assert (await get(api_auth_client, "dune")).json()["groups"] == []


async def test_explicit_type_not_purchased_is_empty_not_402(
    api_auth_client, db_session, test_user, billing_on
):
    from app.modules.estudio.models import Subject

    await add(db_session, Subject(user_id=test_user.id, name="Algebra"))
    resp = await get(api_auth_client, "algebra", types="study")
    assert resp.status_code == 200
    assert resp.json()["groups"] == []


async def test_purchased_and_active_template_appears(
    api_auth_client, db_session, test_user, billing_on
):
    from app.modules.modulos.service import ModulesService

    await _media(db_session, test_user.id)
    await ModulesService(db_session).grant(test_user.id, "media")
    assert titles((await get(api_auth_client, "dune")).json(), "media") == ["Dune"]


async def test_purchased_but_disabled_template_is_hidden_until_reenabled(
    api_auth_client, db_session, test_user, billing_on
):
    from app.modules.modulos.service import ModulesService

    await _media(db_session, test_user.id)
    await ModulesService(db_session).grant(test_user.id, "media")

    await api_auth_client.put("/api/v1/modules/media", json={"enabled": False})
    assert (await get(api_auth_client, "dune")).json()["groups"] == []

    await api_auth_client.put("/api/v1/modules/media", json={"enabled": True})
    assert titles((await get(api_auth_client, "dune")).json(), "media") == ["Dune"]


async def test_purchase_of_another_user_does_not_unlock_mine(
    api_auth_client, db_session, test_user, billing_on
):
    from app.modules.modulos.service import ModulesService

    other = await make_other_user(db_session)
    await ModulesService(db_session).grant(other.id, "media")
    await _media(db_session, test_user.id)
    assert (await get(api_auth_client, "dune")).json()["groups"] == []


async def test_production_without_billing_hides_paid_templates(
    api_auth_client, db_session, test_user, monkeypatch
):
    from app.config import settings

    await _media(db_session, test_user.id)
    # dev sin cobro: aparece (paridad con require_module)
    assert titles((await get(api_auth_client, "dune")).json(), "media") == ["Dune"]
    assert (await api_auth_client.get("/api/v1/media/items")).status_code == 200

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert (await get(api_auth_client, "dune")).json()["groups"] == []
    assert (await api_auth_client.get("/api/v1/media/items")).status_code == 402


async def test_base_types_are_searchable_even_with_billing_on(
    api_auth_client, db_session, test_user, billing_on
):
    await add(db_session, note(test_user.id, "Dune notas"))
    assert titles((await get(api_auth_client, "dune")).json(), "notes") == ["Dune notas"]


# ── 3.9 Rate limit ───────────────────────────────────────────────────────────


async def test_search_is_limited_to_120_per_minute_per_user(api_auth_client):
    for _ in range(120):
        assert (await get(api_auth_client, "cafe")).status_code == 200
    resp = await get(api_auth_client, "cafe")
    assert resp.status_code == 429
    assert int(resp.headers["retry-after"]) >= 1
    assert "muy rápido" in resp.json()["detail"]


async def test_exhausting_one_user_does_not_affect_another(api_auth_client, db_session, monkeypatch):
    from app.core.http_security import search_rate_limiter

    other = await make_other_user(db_session)
    for _ in range(120):
        await search_rate_limiter.hit("alguien-mas")
    assert await search_rate_limiter.hit("alguien-mas") > 0
    # el usuario logueado tiene su propio cupo
    assert (await get(api_auth_client, "cafe")).status_code == 200
    assert other.id != "alguien-mas"


async def test_search_limit_honors_rate_limit_enabled_flag(api_auth_client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    for _ in range(125):
        assert (await get(api_auth_client, "cafe")).status_code == 200


async def test_search_bucket_is_independent_from_auth_and_billing(api_auth_client):
    from app.core.http_security import auth_rate_limiter, billing_rate_limiter, search_rate_limiter

    assert search_rate_limiter is not auth_rate_limiter
    assert search_rate_limiter is not billing_rate_limiter
    for _ in range(121):
        await get(api_auth_client, "cafe")
    # agotar el buscador no bloquea el login
    resp = await api_auth_client.post(
        "/auth/api/login", json={"email": "test@test.com", "password": "test123"}
    )
    assert resp.status_code == 200


# ── 3.10 El termino no queda en los logs ─────────────────────────────────────


async def test_search_term_is_not_written_to_logs(api_auth_client, caplog, monkeypatch):
    import logging

    # Produccion fuerza DEBUG=false (no hay echo de SQLAlchemy). En dev el
    # `echo=True` del engine de la app loguea las sentencias con sus parametros
    # —incluido el termino— y deja el logger de SQLAlchemy en INFO: aca se
    # vuelve a poner como en produccion.
    monkeypatch.setattr(logging.getLogger("sqlalchemy.engine.Engine"), "level", logging.WARNING)
    # LOG_LEVEL por defecto de la app: INFO (aiosqlite en DEBUG volcaria los
    # parametros, pero eso es del driver de tests, no de Postgres en prod).
    caplog.set_level(logging.INFO)
    resp = await get(api_auth_client, "psicologo")
    assert resp.status_code == 200
    # Solo los logs de la app (el cliente httpx del test loguea su propia URL).
    app_records = [r for r in caplog.records if r.name.startswith("app")]
    assert app_records, "el request deberia loguear algo"
    for record in app_records:
        blob = record.getMessage() + " " + repr(record.__dict__)
        assert "psicologo" not in blob.lower()
    assert any(getattr(r, "path", None) == "/api/v1/search" for r in caplog.records)


def test_sentry_scrubs_the_query_string_of_search_events():
    from app.core.sentry import scrub_search_query

    event = {
        "request": {
            "url": "https://app.example.com/api/v1/search",
            "query_string": "q=psicologo&types=notes",
            "method": "GET",
        },
        "transaction": "/api/v1/search",
    }
    cleaned = scrub_search_query(event, {})
    assert "query_string" not in cleaned["request"]
    assert "psicologo" not in repr(cleaned)


def test_sentry_scrub_also_removes_the_term_from_the_url_and_leaves_other_events_alone():
    from app.core.sentry import scrub_search_query

    with_term = {"request": {"url": "https://x.test/api/v1/search?q=psicologo", "query_string": "q=psicologo"}}
    assert "psicologo" not in repr(scrub_search_query(with_term, {}))

    other = {"request": {"url": "https://x.test/api/v1/notes?search=hola", "query_string": "search=hola"}}
    assert scrub_search_query(other, {}) == other
    assert scrub_search_query({"message": "x"}, {}) == {"message": "x"}

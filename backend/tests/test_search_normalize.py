"""Unidades puras del buscador: plegado, escape de LIKE y tokenizado."""
import pytest
from sqlalchemy import column, select, literal
from sqlalchemy.dialects import postgresql, sqlite

BS = chr(92)  # barra invertida

from app.modules.buscador.normalize import (
    FOLD_TABLE,
    escape_like,
    fold,
    fold_text,
    tokenize,
    QueryError,
)



def test_fold_text_removes_accents_and_case():
    assert fold_text("Café") == "cafe"
    assert fold_text("REUNIÓN ANUAL") == "reunion anual"
    assert fold_text("Niña") == "nina"
    assert fold_text("Pingüino") == "pinguino"


def test_fold_text_preserves_length_and_leaves_unmapped_chars():
    for s in ["Café con Juan", "ÁÉÍÓÚÜÑ", "x_y%z\\", "日本語 ABC", "ß ç"]:
        assert len(fold_text(s)) == len(s)
    # Fuera de la tabla no se toca (igual que lower() de SQLite)
    assert fold_text("ç") == "ç"
    assert fold_text("Ç") == "Ç"


def test_fold_table_is_one_char_to_one_char_and_symmetric_in_case():
    assert len(FOLD_TABLE) == 14
    for src, dst in FOLD_TABLE.items():
        assert len(src) == 1 and len(dst) == 1 and dst.isascii()
    assert FOLD_TABLE["Ñ"] == FOLD_TABLE["ñ"] == "n"


def test_escape_like_escapes_backslash_percent_and_underscore():
    assert escape_like("20%") == "20" + BS + "%"
    assert escape_like("mi_a") == "mi" + BS + "_a"
    assert escape_like("a" + BS + "b") == "a" + BS + BS + "b"
    assert escape_like("%%") == BS + "%" + BS + "%"
    assert escape_like("plain") == "plain"


def test_tokenize_trims_collapses_and_folds():
    q, tokens = tokenize("  Café   Con\tJuan ")
    assert q == "Café Con Juan"
    assert tokens == ["cafe", "con", "juan"]


def test_tokenize_drops_control_characters():
    q, tokens = tokenize("ca\x00fe\x07 bar")
    assert q == "cafe bar"
    assert tokens == ["cafe", "bar"]


def test_tokenize_keeps_at_most_five_tokens():
    q, tokens = tokenize("a1 b2 c3 d4 e5 f6 g7")
    assert tokens == ["a1", "b2", "c3", "d4", "e5"]
    # query se devuelve completo (normalizado), los tokens extra solo se ignoran
    assert q == "a1 b2 c3 d4 e5 f6 g7"


@pytest.mark.parametrize("raw", ["", " ", " a ", "a", "\x00a\x00"])
def test_tokenize_rejects_short_queries(raw):
    with pytest.raises(QueryError):
        tokenize(raw)


def test_tokenize_rejects_101_chars_but_accepts_100():
    tokenize("a" * 100)
    with pytest.raises(QueryError):
        tokenize("a" * 101)


def test_tokenize_normalizes_decomposed_unicode():
    # "é" escrita como e + acento combinante (NFD) debe tratarse como "é"
    q, tokens = tokenize("café")
    assert tokens == ["cafe"]


def test_fold_sql_has_same_shape_on_postgres_and_sqlite():
    expr = fold(column("title"))
    pg = str(expr.compile(dialect=postgresql.dialect()))
    lite = str(expr.compile(dialect=sqlite.dialect()))
    for sql in (pg, lite):
        assert sql.count("replace(") == 14
        assert "lower(coalesce(title, " in sql

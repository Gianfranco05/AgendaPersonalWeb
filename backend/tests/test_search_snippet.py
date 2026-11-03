"""Fragmento y resaltado del buscador (funciones puras)."""
from app.modules.buscador.highlight import highlight_ranges, make_snippet


def test_highlight_ranges_are_offsets_on_the_original_text():
    # "Café" ocupa 4 caracteres: el plegado conserva el largo, asi que los
    # offsets valen para el texto con tilde.
    assert highlight_ranges("Café con Juan", ["cafe"]) == [[0, 4]]


def test_highlight_ranges_finds_every_occurrence_of_every_token():
    assert highlight_ranges("Juan, el café de Juan", ["juan", "cafe"]) == [[0, 4], [9, 13], [17, 21]]


def test_highlight_ranges_merge_overlapping_matches():
    # "ana" y "nan" se pisan en "banana": un solo rango
    assert highlight_ranges("banana", ["ana", "nan"]) == [[1, 6]]


def test_highlight_ranges_ignore_case_and_return_empty_without_matches():
    assert highlight_ranges("REUNIÓN", ["reunion"]) == [[0, 7]]
    assert highlight_ranges("nada que ver", ["zzz"]) == []
    assert highlight_ranges(None, ["x"]) == []


def test_snippet_is_a_window_around_the_match_with_ellipsis():
    content = ("palabra " * 120) + "factura de luz " + ("relleno " * 30)
    snippet, ranges = make_snippet([content], ["factura"])
    assert snippet.startswith("…") and snippet.endswith("…")
    assert len(snippet) <= 145
    assert "factura" in snippet
    start, end = ranges[0]
    assert snippet[start:end] == "factura"


def test_snippet_match_near_the_end_has_no_trailing_ellipsis():
    content = ("lorem ipsum " * 150) + "pagar la factura"
    snippet, ranges = make_snippet([content], ["factura"])
    assert snippet.startswith("…")
    assert not snippet.endswith("…")
    assert snippet.endswith("factura")
    assert snippet[ranges[0][0] : ranges[0][1]] == "factura"


def test_snippet_of_short_content_is_returned_whole_without_ellipsis():
    snippet, ranges = make_snippet(["Comprar leche\n\n  y   pan"], ["leche"])
    assert snippet == "Comprar leche y pan"
    assert ranges == [[8, 13]]


def test_snippet_cuts_on_word_boundaries():
    content = "x" * 10 + " " + "abcdefghij " * 40 + "objetivo " + "klmnopqrst " * 40
    snippet, _ = make_snippet([content], ["objetivo"])
    body = snippet.strip("…")
    for word in body.split(" "):
        assert word in ("abcdefghij", "klmnopqrst", "objetivo", "")


def test_snippet_uses_the_first_content_field_that_matches():
    snippet, ranges = make_snippet([None, "sin nada", "tiene Café acá"], ["cafe"])
    assert snippet == "tiene Café acá"
    assert snippet[ranges[0][0] : ranges[0][1]] == "Café"


def test_snippet_when_only_the_title_matched_is_the_start_of_the_content():
    long_content = "inicio del texto " + ("a " * 200)
    snippet, ranges = make_snippet(["", long_content], ["zzz"])
    assert snippet.startswith("inicio del texto")
    assert snippet.endswith("…")
    assert len(snippet) <= 145
    assert ranges == []


def test_snippet_is_none_without_any_content():
    assert make_snippet([None, "", "   "], ["x"]) == (None, [])
    assert make_snippet([], ["x"]) == (None, [])


def test_snippet_returns_html_as_literal_text():
    snippet, ranges = make_snippet(["<b>hola</b> mundo"], ["hola"])
    assert snippet == "<b>hola</b> mundo"
    assert snippet[ranges[0][0] : ranges[0][1]] == "hola"

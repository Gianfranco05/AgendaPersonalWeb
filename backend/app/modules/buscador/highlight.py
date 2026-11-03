"""Fragmento (snippet) y resaltado por offsets.

Nunca se devuelve HTML: los clientes arman el resaltado con los offsets
`[inicio, fin)`, asi que el contenido guardado (que puede traer `<script>`) se
muestra siempre como texto.
"""
import re
from typing import Optional, Sequence

from app.modules.buscador.normalize import fold_text

SNIPPET_LENGTH = 140
#: Cuanto contexto se deja antes de la primera coincidencia.
LEAD_CONTEXT = 40
ELLIPSIS = "…"

_WHITESPACE = re.compile(r"\s+")


def highlight_ranges(text: Optional[str], tokens: Sequence[str]) -> list[list[int]]:
    """Rangos `[inicio, fin)` donde aparece algun token, fusionando los que se pisan.

    Se busca sobre el texto plegado, que tiene el mismo largo que el original.
    """
    if not text or not tokens:
        return []
    folded = fold_text(text)
    spans: list[tuple[int, int]] = []
    for token in tokens:
        if not token:
            continue
        pos = folded.find(token)
        while pos != -1:
            spans.append((pos, pos + len(token)))
            pos = folded.find(token, pos + 1)
    spans.sort()
    merged: list[list[int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def _first_match(folded: str, tokens: Sequence[str]) -> Optional[tuple[int, int]]:
    best: Optional[tuple[int, int]] = None
    for token in tokens:
        if not token:
            continue
        pos = folded.find(token)
        if pos != -1 and (best is None or pos < best[0]):
            best = (pos, pos + len(token))
    return best


def _window(text: str, match: Optional[tuple[int, int]]) -> str:
    """Recorta `text` a ~SNIPPET_LENGTH caracteres cortando en limites de palabra."""
    if len(text) <= SNIPPET_LENGTH:
        return text
    if match is None:
        start = 0
    else:
        start = max(0, match[0] - LEAD_CONTEXT)
    end = start + SNIPPET_LENGTH
    if end >= len(text):
        end = len(text)
        start = max(0, end - SNIPPET_LENGTH)
    # Cortar en palabra sin perder la coincidencia.
    if start > 0 and text[start - 1] != " ":
        nxt = text.find(" ", start)
        limit = match[0] if match else len(text)
        if nxt != -1 and nxt + 1 <= limit:
            start = nxt + 1
    if end < len(text) and text[end] != " ":
        prev = text.rfind(" ", start, end)
        floor = match[1] if match else start
        if prev != -1 and prev >= floor:
            end = prev
    chunk = text[start:end].strip()
    prefix = ELLIPSIS if start > 0 else ""
    suffix = ELLIPSIS if end < len(text) else ""
    return f"{prefix}{chunk}{suffix}"


def make_snippet(
    fields: Sequence[Optional[str]], tokens: Sequence[str]
) -> tuple[Optional[str], list[list[int]]]:
    """Fragmento del primer campo de contenido que coincide, con sus resaltados.

    Si ningun campo de contenido coincide (la coincidencia fue en el titulo o
    en las etiquetas) el fragmento es el inicio del primer contenido no vacio.
    """
    collapsed = [_WHITESPACE.sub(" ", f).strip() for f in fields if f]
    collapsed = [f for f in collapsed if f]
    if not collapsed:
        return None, []
    for text in collapsed:
        match = _first_match(fold_text(text), tokens)
        if match is not None:
            snippet = _window(text, match)
            return snippet, highlight_ranges(snippet, tokens)
    snippet = _window(collapsed[0], None)
    return snippet, highlight_ranges(snippet, tokens)

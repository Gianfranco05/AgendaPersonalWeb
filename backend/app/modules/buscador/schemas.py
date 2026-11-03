from typing import Any, Optional

from pydantic import BaseModel

#: Tipos validos de `types`, en el orden fijo de los grupos.
from app.modules.buscador.sources import TYPE_ORDER

SEARCH_TYPES: tuple[str, ...] = TYPE_ORDER
DEFAULT_LIMIT = 5
MAX_LIMIT = 20


class SearchItem(BaseModel):
    id: str
    type: str
    entity: str
    title: str
    #: Rangos `[inicio, fin)` sobre `title`. Nunca HTML: el cliente arma el resaltado.
    title_highlights: list[list[int]]
    snippet: Optional[str] = None
    snippet_highlights: list[list[int]]
    #: `YYYY-MM-DD` para fechas, UTC con `Z` para timestamps (los eventos van
    #: como hora de pared, sin zona, igual que su API).
    date: Optional[str] = None
    parent_id: Optional[str] = None
    path: str
    meta: Optional[dict[str, Any]] = None


class SearchGroup(BaseModel):
    type: str
    label: str
    has_more: bool
    items: list[SearchItem]


class SearchResponse(BaseModel):
    query: str
    groups: list[SearchGroup]


def parse_types(raw: Optional[str]) -> list[str]:
    """`types=notes,tasks` -> lista validada; vacio o ausente = todos.

    Levanta `ValueError` (mensaje en espanol) ante un valor desconocido.
    """
    if raw is None or not raw.strip():
        return list(SEARCH_TYPES)
    wanted: list[str] = []
    for part in raw.split(","):
        value = part.strip()
        if not value:
            continue
        if value not in SEARCH_TYPES:
            raise ValueError(f"Tipo de búsqueda desconocido: {value[:30]}")
        if value not in wanted:
            wanted.append(value)
    return wanted or list(SEARCH_TYPES)

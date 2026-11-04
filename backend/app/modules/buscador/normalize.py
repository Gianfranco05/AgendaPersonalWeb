"""Plegado de texto, escape de LIKE y tokenizado del buscador.

El plegado (minusculas + sin tildes + n por ene) se hace con la MISMA expresion
SQL en Postgres y SQLite: `lower()` y `replace()` anidados. No se usa `ILIKE`,
`unaccent` ni ninguna extension porque:
  - `lower()` de SQLite solo baja ASCII, y el de Postgres depende de la
    collation de la base (con `C` tampoco baja letras acentuadas), asi que las
    mayusculas acentuadas se mapean explicitamente;
  - dos implementaciones distintas dejan tests verdes con bugs de produccion.

El mapeo es de 1 caracter a 1 caracter: el texto plegado tiene el mismo largo
que el original y los offsets de resaltado calculados sobre el plegado valen
para el original.
"""
import re
import unicodedata

from sqlalchemy import func
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

#: Tabla unica de plegado. Ampliarla es agregar pares aca y en
#: `frontend/src/utils/search.ts` (hay un test que fija ambas).
FOLD_TABLE: dict[str, str] = {
    "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n",
    "Á": "a", "É": "e", "Í": "i", "Ó": "o", "Ú": "u", "Ü": "u", "Ñ": "n",
}

MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 100
MAX_TOKENS = 5

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_WHITESPACE = re.compile(r"\s+")
LIKE_ESCAPE = "\\"


class QueryError(ValueError):
    """La consulta no es valida (mensaje en espanol, listo para el 422)."""


# Armar 14 `replace` anidados con SQLAlchemy cuesta ~3 ms; una busqueda pliega
# decenas de veces las mismas columnas. La expresion es inmutable, asi que se
# arma una vez por columna mapeada y se reutiliza (tambien ahorra generar la
# cache key de la sentencia). La clave es el id del atributo y se guarda el
# atributo junto a la expresion para que ese id no se reutilice.
_FOLD_CACHE: dict[int, tuple] = {}


def _build_fold(col) -> ColumnElement:
    expr = func.lower(func.coalesce(col, ""))
    for src, dst in FOLD_TABLE.items():
        expr = func.replace(expr, src, dst)
    return expr


def fold(col) -> ColumnElement:
    """Expresion SQL que pliega una columna: igual en Postgres y SQLite."""
    if not isinstance(col, InstrumentedAttribute):
        return _build_fold(col)  # columnas sueltas (tests): sin cache
    hit = _FOLD_CACHE.get(id(col))
    if hit is None:
        hit = _FOLD_CACHE[id(col)] = (col, _build_fold(col))
    return hit[1]


def fold_text(text: str) -> str:
    """Mismo plegado que `fold()` pero en Python, preservando el largo.

    Solo baja ASCII y los caracteres de la tabla (como `lower()` de SQLite):
    `str.lower()` completo cambiaria el largo en casos raros (p. ej. `İ`).
    """
    out = []
    for ch in text:
        mapped = FOLD_TABLE.get(ch)
        if mapped is not None:
            out.append(mapped)
        elif ch.isascii():
            out.append(ch.lower())
        else:
            out.append(ch)
    return "".join(out)


def escape_like(text: str) -> str:
    """Escapa la barra invertida, `%` y `_` para usarlos literales con ESCAPE."""
    return (
        text.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", LIKE_ESCAPE + "%")
        .replace("_", LIKE_ESCAPE + "_")
    )


def tokenize(raw: str) -> tuple[str, list[str]]:
    """Devuelve `(query normalizada, tokens plegados)` o levanta `QueryError`.

    La query se normaliza (NFC, sin caracteres de control, espacios colapsados
    y recortada) y debe tener entre 2 y 100 caracteres. Los tokens quedan
    plegados y sin escapar; son como mucho 5, el resto se ignora.
    """
    cleaned = unicodedata.normalize("NFC", raw)
    # Primero los espacios (tab y salto de linea cuentan como separador) y
    # recien despues los caracteres de control restantes.
    cleaned = _WHITESPACE.sub(" ", cleaned)
    cleaned = _CONTROL_CHARS.sub("", cleaned).strip()
    if len(cleaned) < MIN_QUERY_LENGTH:
        raise QueryError(f"Escribí al menos {MIN_QUERY_LENGTH} caracteres para buscar")
    if len(cleaned) > MAX_QUERY_LENGTH:
        raise QueryError(f"La búsqueda no puede tener más de {MAX_QUERY_LENGTH} caracteres")
    tokens = [fold_text(t) for t in cleaned.split(" ")][:MAX_TOKENS]
    return cleaned, tokens

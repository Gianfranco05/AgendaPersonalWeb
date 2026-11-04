"""Categoria sugerida para un movimiento importado.

Orden (la primera que da resultado): historial exacto del usuario, historial
por palabra clave y reglas fijas por palabra clave. Una sola consulta de
historial por preview, acotada por `user_id` y por fecha.
"""

import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finanzas.models import Category, Transaction
from app.modules.finanzas.transfer.import_parse import strip_accents

HISTORY_MONTHS = 24
HISTORY_MAX_ROWS = 20_000
MIN_WORD_LEN = 4

STOPWORDS = frozenset(
    "pago pagos compra compras transferencia transferencias debito credito mercadopago mercado "
    "pagar cobro cuenta cuota debin recibida recibido enviada enviado banco".split()
)

# palabra clave -> rubro (merchant_category del enum existente)
KEYWORD_RULES: dict[str, tuple[str, ...]] = {
    "grocery": ("coto", "carrefour", "dia", "jumbo", "disco", "vea", "changomas", "supermercado", "verduleria"),
    "transportation": ("uber", "cabify", "didi", "sube", "ypf", "shell", "axion", "peaje", "estacionamiento"),
    "utilities": (
        "edenor", "edesur", "metrogas", "naturgy", "aysa", "personal", "movistar", "claro",
        "telecentro", "fibertel", "flow",
    ),
    "entertainment": ("netflix", "spotify", "disney", "hbo", "max", "prime video", "steam", "cine"),
    "dining": ("rappi", "pedidosya", "mcdonald", "burger", "cafe", "resto"),
    "healthcare": ("farmacia", "farmacity", "osde", "swiss medical", "galeno"),
    "education": ("utn", "universidad", "curso", "udemy"),
    "shopping": ("mercadolibre", "mercado libre", "falabella", "garbarino"),
    "services": ("afip", "arca", "rentas", "municipalidad", "seguro"),
}

# rubro -> nombres de categoria del usuario (normalizados) que lo representan
CATEGORY_SYNONYMS: dict[str, tuple[str, ...]] = {
    "grocery": ("supermercado", "comida", "alimentos", "almacen", "alimentacion", "mercaderia"),
    "transportation": ("transporte", "auto", "nafta", "viajes", "movilidad"),
    "utilities": ("servicios", "facturas", "impuestos y servicios", "telefono", "internet", "hogar"),
    "entertainment": ("entretenimiento", "ocio", "suscripciones", "streaming", "salidas"),
    "dining": ("restaurantes", "comidas", "delivery", "salidas", "comida"),
    "healthcare": ("salud", "farmacia", "medicina"),
    "education": ("educacion", "estudio", "cursos"),
    "shopping": ("compras", "ropa", "shopping"),
    "services": ("servicios", "impuestos", "tramites"),
}


def normalize_desc(text: str) -> str:
    """minusculas, sin tildes, sin digitos ni signos, espacios colapsados."""
    t = strip_accents(str(text)).lower()
    t = re.sub(r"[^a-z\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def significant_words(norm: str) -> list[str]:
    return [w for w in norm.split() if len(w) >= MIN_WORD_LEN and w not in STOPWORDS]


def merchant_rule(norm: str) -> Optional[str]:
    padded = f" {norm} "
    tokens = set(norm.split())
    for rubro, words in KEYWORD_RULES.items():
        for w in words:
            if (" " in w and f" {w} " in padded) or w in tokens:
                return rubro
    return None


def _top(counter: Counter) -> Optional[str]:
    return counter.most_common(1)[0][0] if counter else None


class Suggester:
    def __init__(self, categories: list[Category], history: list[tuple[str, str, str]]):
        # nombre normalizado -> id (la primera por nombre)
        self._cat_by_name: dict[str, str] = {}
        for c in categories:
            self._cat_by_name.setdefault(normalize_desc(c.name), c.id)
        self._exact: dict[tuple[str, str], Counter] = defaultdict(Counter)
        self._word: dict[tuple[str, str], Counter] = defaultdict(Counter)
        for desc, tx_type, category_id in history:
            norm = normalize_desc(desc)
            if not norm:
                continue
            self._exact[(norm, tx_type)][category_id] += 1
            for w in set(significant_words(norm)):
                self._word[(w, tx_type)][category_id] += 1

    @classmethod
    async def load(cls, db: AsyncSession, user_id: str, today: date) -> "Suggester":
        categories = (
            (await db.execute(select(Category).where(Category.user_id == user_id))).scalars().all()
        )
        since = today - timedelta(days=30 * HISTORY_MONTHS)
        rows = (
            await db.execute(
                select(Transaction.product_name, Transaction.type, Transaction.category_id)
                .where(
                    Transaction.user_id == user_id,
                    Transaction.is_deleted == False,  # noqa: E712
                    Transaction.category_id.is_not(None),
                    Transaction.transaction_date >= since,
                )
                .order_by(Transaction.transaction_date.desc())
                .limit(HISTORY_MAX_ROWS)
            )
        ).all()
        valid = {c.id for c in categories}
        return cls(categories, [(d, t, c) for d, t, c in rows if c in valid])

    def _category_for_rubro(self, rubro: str) -> Optional[str]:
        for name in CATEGORY_SYNONYMS.get(rubro, ()):
            cid = self._cat_by_name.get(name)
            if cid:
                return cid
        return None

    def suggest(self, description: str, tx_type: str) -> tuple[Optional[str], str, str]:
        """(category_id, fuente, merchant_category). Fuente: history | rule | none."""
        norm = normalize_desc(description)
        rubro = merchant_rule(norm)
        merchant_category = rubro or "other"
        exact = _top(self._exact.get((norm, tx_type), Counter()))
        if exact:
            return exact, "history", merchant_category
        words = significant_words(norm)
        if words:
            by_word = _top(self._word.get((words[0], tx_type), Counter()))
            if by_word:
                return by_word, "history", merchant_category
        if rubro:
            cid = self._category_for_rubro(rubro)
            if cid:
                return cid, "rule", merchant_category
        return None, "none", merchant_category

"""Valuacion de inversiones: calculos puros, sin base de datos ni HTTP.

Todo el dinero se maneja en `Decimal` con redondeo half-up a 2 decimales en lo
que sale de la API. SQLite devuelve `float` en las columnas `Numeric`, asi que
todo lo que se lee de la base pasa por `to_decimal` (que va por `str`, no por
el float crudo, para no arrastrar 0.1 + 0.2).
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, NamedTuple, Optional, Protocol

ZERO = Decimal("0")
CENT = Decimal("0.01")
DAYS_IN_YEAR = Decimal(365)

#: Monedas en las que se puede cargar un activo. USDT se valua 1:1 con USD.
CURRENCIES = ("ARS", "USD", "USDT", "EUR")
#: Un plazo fijo solo existe en pesos o dolares.
FIXED_TERM_CURRENCIES = ("ARS", "USD")
FIXED_TERM = "fixed_term"


def to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round2(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


# ── Plazo fijo ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FixedTermInfo:
    term_days: int
    interest_total: Decimal
    amount_at_maturity: Decimal
    accrued_interest: Decimal
    tea_pct: Decimal


def term_days(start: date, maturity: date) -> int:
    return (maturity - start).days


def _simple_interest(principal: Decimal, tna_pct: Decimal, days: int) -> Decimal:
    """Interes simple, convencion argentina TNA/365."""
    return round2(principal * tna_pct / Decimal(100) * Decimal(days) / DAYS_IN_YEAR)


def tea_pct(tna_pct: Decimal, days: int) -> Decimal:
    """TEA equivalente al plazo. Es informativa: se calcula con float y se cuantiza."""
    if days <= 0:
        return ZERO
    factor = 1.0 + float(tna_pct) / 100.0 * days / 365.0
    return round2(Decimal(str((factor ** (365.0 / days) - 1.0) * 100.0)))


def fixed_term_info(
    principal: Decimal, tna_pct: Decimal, start: date, maturity: date, today: date
) -> FixedTermInfo:
    days = term_days(start, maturity)
    total = _simple_interest(principal, tna_pct, days)
    # El devengado arranca en 0 antes del inicio y se frena en el vencimiento.
    elapsed = min(max((today - start).days, 0), days)
    return FixedTermInfo(
        term_days=days,
        interest_total=total,
        amount_at_maturity=principal + total,
        accrued_interest=_simple_interest(principal, tna_pct, elapsed),
        tea_pct=tea_pct(tna_pct, days),
    )


# ── Valor efectivo ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Valuation:
    invested_amount: Decimal
    effective_value: Decimal
    #: quote | manual | fixed_term_accrued | invested
    value_source: str
    gain: Decimal
    gain_pct: Optional[Decimal]
    days_to_maturity: Optional[int]
    is_matured: bool
    fixed_term: Optional[FixedTermInfo]


def valuate(inv: Any, today: date) -> Valuation:
    """Valor efectivo y derivados de un activo (cualquier objeto con los
    atributos del modelo `Investment`).

    Precedencia: cotizacion automatica -> valor manual -> plazo fijo devengado
    -> lo invertido.
    """
    invested = round2(to_decimal(inv.invested_amount))
    quantity = to_decimal(inv.quantity)
    last_price = to_decimal(inv.last_price)
    current = to_decimal(inv.current_value)
    tna = to_decimal(inv.interest_rate_tna)

    ft: Optional[FixedTermInfo] = None
    if inv.asset_type == FIXED_TERM and tna is not None and inv.start_date and inv.maturity_date:
        if inv.maturity_date > inv.start_date:
            ft = fixed_term_info(invested, tna, inv.start_date, inv.maturity_date, today)

    if inv.price_source != "manual" and quantity is not None and last_price is not None:
        value, source = round2(quantity * last_price), "quote"
    elif current is not None:
        value, source = round2(current), "manual"
    elif ft is not None:
        value, source = invested + ft.accrued_interest, "fixed_term_accrued"
    else:
        value, source = invested, "invested"

    gain = value - invested
    gain_pct = round2(gain / invested * Decimal(100)) if invested > 0 else None

    days_left = (inv.maturity_date - today).days if inv.maturity_date else None
    return Valuation(
        invested_amount=invested,
        effective_value=value,
        value_source=source,
        gain=gain,
        gain_pct=gain_pct,
        days_to_maturity=days_left,
        is_matured=days_left is not None and days_left < 0,
        fixed_term=ft,
    )


# ── Conversion de moneda y totales ──────────────────────────────────────────


@dataclass(frozen=True)
class Rates:
    usd_ars: Optional[Decimal] = None
    eur_ars: Optional[Decimal] = None


@dataclass(frozen=True)
class Totals:
    total_ars: Optional[Decimal]
    total_usd: Optional[Decimal]
    missing_rates: list[str]


def compute_totals(subtotals: dict[str, Decimal], rates: Rates) -> Totals:
    """Totales en ARS y USD a partir de los subtotales por moneda.

    Se suma primero por moneda (exacto) y se convierte despues, redondeando una
    sola vez al final. USD y USDT valen lo mismo y no pasan por ARS para el
    total en dolares. Lo que no se puede calcular por falta de cotizacion sale
    `None` y el par faltante queda en `missing_rates` (en el orden USD, EUR).
    Sin ningun activo ambos totales valen 0.
    """
    has_ars = "ARS" in subtotals
    has_usd = "USD" in subtotals or "USDT" in subtotals
    has_eur = "EUR" in subtotals
    ars = subtotals.get("ARS", ZERO)
    usd = subtotals.get("USD", ZERO) + subtotals.get("USDT", ZERO)
    eur = subtotals.get("EUR", ZERO)
    usd_rate, eur_rate = rates.usd_ars, rates.eur_ars

    no_usd_rate = usd_rate is None
    no_eur_rate = eur_rate is None

    missing: list[str] = []
    if no_usd_rate and (has_usd or has_ars or has_eur):
        missing.append("USD")
    if no_eur_rate and has_eur:
        missing.append("EUR")

    total_ars: Optional[Decimal] = None
    if not (has_usd and no_usd_rate) and not (has_eur and no_eur_rate):
        total_ars = round2(ars + usd * (usd_rate or ZERO) + eur * (eur_rate or ZERO))

    total_usd: Optional[Decimal] = None
    if not ((has_ars or has_eur) and no_usd_rate) and not (has_eur and no_eur_rate):
        in_ars = ars + eur * (eur_rate or ZERO)
        total_usd = round2(usd + (in_ars / usd_rate if usd_rate else ZERO))

    return Totals(total_ars, total_usd, missing)


def convert_to_ars(amount: Decimal, currency: str, rates: Rates) -> Optional[Decimal]:
    """Un monto en su moneda a ARS, o None si falta la cotizacion."""
    if currency == "ARS":
        return amount
    rate = rates.eur_ars if currency == "EUR" else rates.usd_ars
    return None if rate is None else amount * rate


# ── Formato ─────────────────────────────────────────────────────────────────

_SYMBOLS = {"ARS": "$", "USD": "US$", "USDT": "USDT", "EUR": "€"}


def format_money_es_ar(amount: Decimal, currency: str = "ARS") -> str:
    """`$ 1.024.657,53 ARS` (miles con punto, decimales con coma)."""
    text = f"{round2(amount):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{_SYMBOLS.get(currency, currency)} {text} {currency}"


# ── Punto de extension: cotizaciones automaticas ────────────────────────────


class PriceQuote(NamedTuple):
    price: Decimal
    currency: str
    as_of: datetime


class PriceProvider(Protocol):
    """Un proveedor de precios (CoinGecko, BYMA...). Sumar uno = implementar la
    clase y registrarla en `PRICE_PROVIDERS`; el esquema no cambia porque el
    modelo ya guarda `ticker`, `price_source`, `last_price` y `last_price_at`.
    """

    key: str
    supported_types: frozenset[str]

    async def quote(self, ticker: str, currency: str) -> Optional[PriceQuote]: ...


#: Vacio en esta etapa: la valuacion es manual y no hay llamadas HTTP externas.
PRICE_PROVIDERS: dict[str, PriceProvider] = {}


async def refresh_quotes(db: Any, user_id: str) -> int:
    """Actualiza `last_price` de los activos con proveedor automatico. No-op
    hoy (no hay proveedores): devuelve la cantidad de activos actualizados."""
    return 0

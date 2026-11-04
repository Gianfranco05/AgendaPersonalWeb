"""Formato de celdas y textos del export (es-AR), sin `locale`.

`locale.setlocale` es global al proceso y la imagen slim no trae locales: el
formato se arma a mano.
"""

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

# Prefijos que Excel/Sheets interpretan como formula (OWASP CSV injection).
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")

TYPE_LABELS = {"income": "Ingreso", "expense": "Egreso"}
PAYMENT_LABELS = {
    "cash": "Efectivo",
    "debit_card": "Tarjeta de débito",
    "credit_card": "Tarjeta de crédito",
    "transfer": "Transferencia",
    "check": "Cheque",
    "other": "Otro",
}
ACCOUNT_TYPE_LABELS = {
    "checking": "Cuenta corriente",
    "savings": "Caja de ahorro",
    "credit": "Crédito",
    "cash": "Efectivo",
    "investment": "Inversión",
}
_CURRENCY_SYMBOLS = {"ARS": "$", "USD": "US$", "EUR": "€"}

# Control chars salvo \t \n \r (que safe_text trata aparte).
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def safe_text(value: Optional[str]) -> str:
    """Texto seguro para una celda: si empieza con `= + - @ \t \r \n` se le
    antepone `'` para que ningun programa de planillas lo evalue como formula."""
    if value is None:
        return ""
    text = _CONTROL.sub("", str(value))
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def pdf_safe(value: Optional[str]) -> str:
    """Quita lo que Helvetica (WinAnsi / cp1252) no puede dibujar, p. ej. emojis."""
    if value is None:
        return ""
    text = _CONTROL.sub("", str(value)).replace("\t", " ").replace("\r", " ").replace("\n", " ")
    return text.encode("cp1252", errors="ignore").decode("cp1252")


def _group_thousands(integer: str) -> str:
    out = []
    while len(integer) > 3:
        out.insert(0, integer[-3:])
        integer = integer[:-3]
    out.insert(0, integer)
    return ".".join(out)


def format_number_ar(amount: Decimal) -> str:
    q = Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "-" if q < 0 else ""
    integer, _, frac = f"{abs(q):f}".partition(".")
    return f"{sign}{_group_thousands(integer)},{frac or '00'}"


def format_money_ar(amount: Decimal, currency: str) -> str:
    """`$ 1.234,56`, `US$ 1.234,56`, `€ 1.234,56`; otra moneda lleva su codigo."""
    number = format_number_ar(abs(Decimal(amount)))
    q = Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "-" if q < 0 else ""
    symbol = _CURRENCY_SYMBOLS.get(currency, currency)
    return f"{sign}{symbol} {number}"


def format_date_ar(d: date) -> str:
    return d.strftime("%d/%m/%Y")

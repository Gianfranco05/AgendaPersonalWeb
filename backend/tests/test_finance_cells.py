from datetime import date
from decimal import Decimal

import pytest

from app.modules.finanzas.transfer import cells


@pytest.mark.parametrize(
    "raw",
    ['=HYPERLINK("http://x","clic")', "+1", "-2+3", "@SUM(A1)", "\tcmd", "\rcmd", "\ncmd"],
)
def test_safe_text_escapa_inicios_peligrosos(raw):
    assert cells.safe_text(raw) == "'" + raw


@pytest.mark.parametrize("raw", ["Supermercado", "1 + 1", "a=b", "", "Coto -20%"])
def test_safe_text_deja_el_resto_igual(raw):
    assert cells.safe_text(raw) == raw


def test_safe_text_none_es_vacio():
    assert cells.safe_text(None) == ""


def test_pdf_safe_quita_emojis_y_conserva_acentos():
    assert cells.pdf_safe("Café ☕ ñandú 🍕 € ok") == "Café  ñandú  € ok"


def test_pdf_safe_none():
    assert cells.pdf_safe(None) == ""


def test_format_money_ar_pesos_dolares_euros():
    assert cells.format_money_ar(Decimal("1234.5"), "ARS") == "$ 1.234,50"
    assert cells.format_money_ar(Decimal("1234567.891"), "USD") == "US$ 1.234.567,89"
    assert cells.format_money_ar(Decimal("-0.5"), "EUR") == "-€ 0,50"


def test_format_money_ar_moneda_desconocida_usa_el_codigo():
    assert cells.format_money_ar(Decimal("10"), "UYU") == "UYU 10,00"


def test_format_date_ar():
    assert cells.format_date_ar(date(2026, 10, 5)) == "05/10/2026"

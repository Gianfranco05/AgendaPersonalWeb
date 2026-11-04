import pytest

from app.modules.finanzas.transfer import import_presets as pr
from app.modules.finanzas.transfer.import_parse import normalize_header
from app.modules.finanzas.transfer.import_rules import (
    Suggester,
    merchant_rule,
    normalize_desc,
    significant_words,
)


def test_normalize_desc_quita_tildes_digitos_y_signos():
    assert normalize_desc("COMPRA Café-Martínez  Nº 123!") == "compra cafe martinez no"


@pytest.mark.parametrize(
    "desc,rubro",
    [
        ("compra coto sucursal", "grocery"),
        ("pago uber trip", "transportation"),
        ("netflix com", "entertainment"),
        ("swiss medical cuota", "healthcare"),  # palabra compuesta
        ("mercado libre envio", "shopping"),
        ("cotona de trabajo", None),  # "coto" dentro de otra palabra no matchea
        ("", None),
    ],
)
def test_merchant_rule(desc, rubro):
    assert merchant_rule(normalize_desc(desc)) == rubro


def test_palabras_significativas_ignoran_vacias_y_cortas():
    assert significant_words("pago de coto sur") == ["coto"]
    assert significant_words("transferencia mercadopago") == []


def test_suggester_prioriza_historial_y_separa_por_tipo():
    class Cat:
        def __init__(self, id, name):
            self.id, self.name = id, name

    s = Suggester(
        [Cat("c1", "Supermercado"), Cat("c2", "Otros")],
        [("Coto 123", "expense", "c2"), ("Coto 456", "expense", "c2"), ("Coto 9", "expense", "c1")],
    )
    assert s.suggest("COTO 777", "expense") == ("c2", "history", "grocery")
    # Otro tipo: el historial de gastos no aplica; cae a la regla.
    assert s.suggest("COTO 777", "income") == ("c1", "rule", "grocery")
    assert s.suggest("zzz qqq", "expense") == (None, "none", "other")


@pytest.mark.parametrize(
    "headers,expected",
    [
        (["DATE", "SOURCE_ID", "EXTERNAL_REFERENCE", "RECORD_TYPE", "DESCRIPTION", "NET_CREDIT_AMOUNT", "NET_DEBIT_AMOUNT"], pr.MP_RELEASE),
        (["TRANSACTION_DATE", "SOURCE_ID", "TRANSACTION_TYPE", "TRANSACTION_AMOUNT"], pr.MP_ACCOUNT),
        (["Fecha", "Concepto", "Importe"], pr.GENERIC),
        (["TRANSACTION_DATE", "SOURCE_ID", "TRANSACTION_TYPE"], pr.GENERIC),  # sin columna de monto
    ],
)
def test_detect_preset(headers, expected):
    assert pr.detect_preset([normalize_header(h) for h in headers]) == expected


def test_mapeo_de_mercado_pago_apunta_a_las_columnas_correctas():
    h = [normalize_header(x) for x in ["X", "DATE", "RECORD_TYPE", "NET_CREDIT_AMOUNT", "NET_DEBIT_AMOUNT", "DESCRIPTION", "SOURCE_ID"]]
    m = pr.build_mapping(pr.MP_RELEASE, h)
    assert (m.date, m.credit, m.debit, m.reference, m.amount_mode) == (1, 3, 4, 6, "debit_credit")
    assert m.include_when.column == 2 and m.include_when.values == ["release"]


@pytest.mark.parametrize(
    "table,value,expected",
    [("mp_release", "payment", "Cobro"), ("mp_release", "tax_iva", "Impuesto / retención"),
     ("mp_release", "raro_codigo", "raro_codigo"), ("mp_account", "WITHDRAWAL_CANCEL", "Retiro cancelado")],
)
def test_translate(table, value, expected):
    assert pr.translate(table, value) == expected

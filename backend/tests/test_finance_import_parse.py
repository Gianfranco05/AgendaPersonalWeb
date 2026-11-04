import io
import zipfile
from datetime import date, time
from decimal import Decimal

import pytest
from openpyxl import Workbook

from app.config import settings
from app.modules.finanzas.transfer import import_parse as ip

TODAY = date(2026, 11, 4)


def _xlsx(rows, sheet_state=None) -> bytes:
    wb = Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── Tipo y limites del archivo ──────────────────────────────────────────────


def test_detect_kind_por_contenido_no_por_extension():
    assert ip.detect_kind(_xlsx([["a"]])) == "xlsx"
    assert ip.detect_kind(b"fecha;monto\n1;2\n") == "csv"


@pytest.mark.parametrize(
    "blob,msg",
    [
        (b"%PDF-1.7\n" + b"\x00" * 10, "csv o .xlsx"),
        (b"\x00\x01\x02binario", "csv o .xlsx"),
        (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"x" * 50, "xlsx"),
    ],
)
def test_detect_kind_rechaza_binarios_con_415(blob, msg):
    with pytest.raises(ip.ImportFileError) as e:
        ip.detect_kind(blob)
    assert e.value.status_code == 415
    assert msg in e.value.detail


def test_xls_viejo_explica_como_convertirlo():
    with pytest.raises(ip.ImportFileError) as e:
        ip.detect_kind(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"x" * 50)
    assert ".xls" in e.value.detail and "guardalo" in e.value.detail


# ── CSV ─────────────────────────────────────────────────────────────────────


def test_csv_utf8_con_bom_y_punto_y_coma():
    data = "﻿fecha;descripción;monto\n01/10/2026;Café;1.234,56\n".encode("utf-8")
    t = ip.load_table(data)
    assert t.kind == "csv"
    assert t.rows[0] == ["fecha", "descripción", "monto"]
    assert t.rows[1] == ["01/10/2026", "Café", "1.234,56"]


def test_csv_cp1252_cae_cuando_no_es_utf8():
    data = "Fecha;Concepto;Débito\n01/10/2026;Pago año;10,00\n".encode("cp1252")
    t = ip.load_table(data)
    assert t.rows[1][1] == "Pago año" and t.rows[0][2] == "Débito"


@pytest.mark.parametrize("sep", [",", ";", "\t", "|"])
def test_csv_detecta_separador(sep):
    data = f"a{sep}b{sep}c\n1{sep}2{sep}3\n".encode()
    assert ip.load_table(data).rows == [["a", "b", "c"], ["1", "2", "3"]]


def test_csv_comillas_con_separador_adentro():
    data = b'fecha,desc,monto\n2026-10-01,"Coto, sucursal 4","10.50"\n'
    t = ip.load_table(data)
    assert t.rows[1] == ["2026-10-01", "Coto, sucursal 4", "10.50"]


def test_csv_descarta_filas_totalmente_vacias_y_trunca_celdas():
    data = ("a;b\n\n;\n" + "x" * 900 + ";y\n").encode()
    t = ip.load_table(data)
    assert len(t.rows) == 2
    assert len(t.rows[1][0]) == 500


def test_csv_tope_de_filas_dev_422(monkeypatch):
    monkeypatch.setattr(settings, "FINANCE_IMPORT_MAX_ROWS", 3)
    ok = "a;b\n1;1\n2;2\n3;3\n".encode()
    assert len(ip.load_table(ok).rows) == 4  # encabezado + 3
    with pytest.raises(ip.ImportFileError) as e:
        ip.load_table("a;b\n1;1\n2;2\n3;3\n4;4\n".encode())
    assert e.value.status_code == 422 and "3" in e.value.detail


def test_csv_tope_de_columnas(monkeypatch):
    monkeypatch.setattr(settings, "FINANCE_IMPORT_MAX_COLUMNS", 4)
    with pytest.raises(ip.ImportFileError) as e:
        ip.load_table(b"a;b;c;d;e\n1;2;3;4;5\n")
    assert e.value.status_code == 422 and "columnas" in e.value.detail


# ── XLSX ────────────────────────────────────────────────────────────────────


def test_xlsx_valores_numeros_y_fechas():
    from datetime import datetime

    data = _xlsx([["Fecha", "Monto", "Detalle"], [datetime(2026, 10, 3, 14, 5), 1234.5, "Café"]])
    t = ip.load_table(data)
    assert t.kind == "xlsx"
    assert t.rows[1] == ["2026-10-03T14:05:00", "1234.5", "Café"]


def test_xlsx_formula_sin_valor_cacheado_no_se_evalua():
    # openpyxl escribe la formula sin valor cacheado: nunca se calcula.
    data = _xlsx([["Fecha", "Monto"], ["2026-10-01", "=1+1"]])
    t = ip.load_table(data)
    assert t.rows[1][1] == ip.FORMULA_NO_VALUE


def test_xlsx_zip_bomb_por_ratio_o_tamano():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("xl/worksheets/sheet1.xml", b"\x00" * (30 * 1024 * 1024))
    with pytest.raises(ip.ImportFileError) as e:
        ip.load_table(buf.getvalue())
    assert e.value.status_code in (413, 422)


def test_xlsx_con_macros_se_rechaza():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("xl/vbaProject.bin", b"macro")
    with pytest.raises(ip.ImportFileError) as e:
        ip.load_table(buf.getvalue())
    assert "macros" in e.value.detail


def test_xlsx_con_rutas_peligrosas_se_rechaza():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("../evil.txt", b"x")
    with pytest.raises(ip.ImportFileError):
        ip.load_table(buf.getvalue())


def test_xlsx_demasiadas_entradas():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for i in range(250):
            z.writestr(f"f{i}.txt", b"x")
    with pytest.raises(ip.ImportFileError):
        ip.load_table(buf.getvalue())


def test_xlsx_con_entidad_xml_no_expande():
    # billion laughs en el sheet: defusedxml tiene que cortarlo.
    base = io.BytesIO(_xlsx([["a", "b"], ["1", "2"]]))
    out = io.BytesIO()
    with zipfile.ZipFile(base) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            blob = zin.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                blob = blob.replace(
                    b"<worksheet",
                    b'<!DOCTYPE x [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;&a;">]><worksheet',
                    1,
                )
            zout.writestr(item, blob)
    with pytest.raises(ip.ImportFileError):
        ip.load_table(out.getvalue())


# ── Encabezado ──────────────────────────────────────────────────────────────


def test_normalize_header():
    assert ip.normalize_header("  Fecha  de Operación ") == "fecha de operacion"
    assert ip.normalize_header("NET_CREDIT_AMOUNT") == "net credit amount"
    assert ip.normalize_header("Débito") == "debito"


def test_find_header_row_salta_el_preambulo_del_banco():
    rows = [
        ["Banco Ejemplo", ""],
        ["Cuenta: 1234", ""],
        [],
        ["Fecha", "Concepto", "Débito", "Crédito", "Saldo"],
        ["01/10/2026", "Super", "10,00", "", "90,00"],
    ]
    assert ip.find_header_row(rows) == 3


def test_find_header_row_default_cero():
    assert ip.find_header_row([["x", "y"], ["1", "2"]]) == 0


# ── Fechas ──────────────────────────────────────────────────────────────────


def test_fecha_iso_con_offset_se_pasa_a_hora_local_del_usuario():
    # 23:30 en GMT-4 = 00:30 del dia siguiente en Argentina (UTC-3).
    d, t = ip.parse_datetime_cell("2026-10-03T23:30:10-04:00", True, -180, TODAY)
    assert (d, t) == (date(2026, 10, 4), time(0, 30, 10))
    d, t = ip.parse_datetime_cell("2026-10-03T14:05:10-04:00", True, -180, TODAY)
    assert (d, t) == (date(2026, 10, 3), time(15, 5, 10))


def test_fecha_iso_sin_zona_queda_tal_cual():
    assert ip.parse_datetime_cell("2026-10-03T14:05:10", True, -180, TODAY) == (
        date(2026, 10, 3),
        time(14, 5, 10),
    )
    assert ip.parse_datetime_cell("2026-10-03", True, -180, TODAY) == (date(2026, 10, 3), None)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("03/10/2026", date(2026, 10, 3)),
        ("03-10-2026", date(2026, 10, 3)),
        ("03.10.2026", date(2026, 10, 3)),
        ("3/10/26", date(2026, 10, 3)),
    ],
)
def test_fecha_dia_primero(raw, expected):
    assert ip.parse_datetime_cell(raw, True, 0, TODAY)[0] == expected


def test_fecha_mes_primero_cuando_se_pide():
    assert ip.parse_datetime_cell("10/03/2026", False, 0, TODAY)[0] == date(2026, 10, 3)


def test_fecha_con_hora_en_texto_es_ar():
    assert ip.parse_datetime_cell("03/10/2026 14:05", True, 0, TODAY) == (
        date(2026, 10, 3),
        time(14, 5),
    )


def test_fecha_serial_de_excel():
    # 46298 = 2026-10-03
    assert ip.parse_datetime_cell("46298", True, 0, TODAY)[0] == date(2026, 10, 3)


@pytest.mark.parametrize("raw", ["", "no es fecha", "31/02/2026", "13/13/2026", "01/01/1999"])
def test_fecha_invalida_o_fuera_de_rango(raw):
    with pytest.raises(ValueError):
        ip.parse_datetime_cell(raw, True, 0, TODAY)


def test_fecha_en_el_futuro_lejano_se_rechaza():
    with pytest.raises(ValueError):
        ip.parse_datetime_cell("2028-01-01", True, 0, TODAY)
    assert ip.parse_datetime_cell("2027-06-01", True, 0, TODAY)[0] == date(2027, 6, 1)


def test_detect_dayfirst_por_columna():
    assert ip.detect_dayfirst(["13/01/2026", "01/02/2026"]) == (True, False)
    assert ip.detect_dayfirst(["01/13/2026", "02/01/2026"]) == (False, False)
    # Ambigua: queda dd/mm (es-AR) y avisa.
    assert ip.detect_dayfirst(["01/02/2026", "03/04/2026"]) == (True, True)
    # ISO no es ambigua.
    assert ip.detect_dayfirst(["2026-01-02"]) == (True, False)


# ── Numeros ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1.234,56", "1234.56"),
        ("$ 1.234,56", "1234.56"),
        ("-1.234,56", "-1234.56"),
        ("$ -1.234,56", "-1234.56"),
        ("(1.234,56)", "-1234.56"),
        ("1.234,56-", "-1234.56"),
        ("US$ 10,5", "10.50"),
        ("ARS 1.000", "1000.00"),
        ("1,234.56", "1234.56"),
        ("1234.56", "1234.56"),
        ("1234,56", "1234.56"),
        ("1.234.567,8", "1234567.80"),
        ("0,005", "0.01"),
        (" 1 000,50 ", "1000.50"),
    ],
)
def test_parse_amount_auto(raw, expected):
    assert ip.parse_amount(raw) == Decimal(expected)


def test_parse_amount_override_explicito_no_adivina():
    assert ip.parse_amount("1.234", "." ) == Decimal("1.23")
    assert ip.parse_amount("1.234", ",") == Decimal("1234.00")
    assert ip.parse_amount("1,234", ".") == Decimal("1234.00")


def test_parse_amount_un_punto_con_tres_digitos_depende_de_la_columna():
    assert ip.parse_amount("1.234", "auto", dot_mode="thousands") == Decimal("1234.00")
    assert ip.parse_amount("1.234", "auto", dot_mode="decimal") == Decimal("1.23")


def test_infer_dot_mode():
    assert ip.infer_dot_mode(["1.234", "5.000", "20"]) == "thousands"
    assert ip.infer_dot_mode(["1234.5", "1.234"]) == "decimal"
    assert ip.infer_dot_mode(["12.50"]) == "decimal"
    assert ip.infer_dot_mode(["1.234,50", "1.234"]) == "thousands"


@pytest.mark.parametrize("raw", ["", "abc", "12abc", "1e5", "1,2,3,4x", "--5"])
def test_parse_amount_invalido(raw):
    with pytest.raises(ValueError):
        ip.parse_amount(raw)


def test_parse_amount_tope_money():
    assert ip.parse_amount("9.999.999.999,99") == Decimal("9999999999.99")
    with pytest.raises(ValueError) as e:
        ip.parse_amount("10.000.000.000,00")
    assert "fuera de rango" in str(e.value)


def test_parse_amount_es_decimal_exacto_no_float():
    assert ip.parse_amount("0,10") + ip.parse_amount("0,20") == Decimal("0.30")


@pytest.mark.parametrize(
    "raw,expected",
    [("$", "ARS"), ("ARS", "ARS"), ("u$s", "USD"), ("US$", "USD"), ("dolares", "USD"),
     ("EUR", "EUR"), ("€", "EUR"), ("brl", "BRL"), ("", None)],
)
def test_normalize_currency(raw, expected):
    assert ip.normalize_currency(raw) == expected


def test_normalize_currency_no_permitida():
    with pytest.raises(ValueError):
        ip.normalize_currency("XYZ")


def test_sanitize_description_colapsa_y_limpia():
    assert ip.sanitize_text("  Pago \t  Coto\x00\x07  ") == "Pago Coto"

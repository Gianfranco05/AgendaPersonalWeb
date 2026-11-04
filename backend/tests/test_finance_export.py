import io
from datetime import date, datetime
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from openpyxl import load_workbook

from app.config import settings
from app.main import app
from app.modules.finanzas.models import BankAccount, Category, Transaction
from app.modules.inversiones.models import Investment
from app.modules.recurrentes.models import RecurringTransaction

pytestmark = pytest.mark.asyncio

URL = "/api/v1/finance/export"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
RANGE = {"date_from": "2026-10-01", "date_to": "2026-10-31"}


def _tx(user_id, amount, type="expense", day="2026-10-05", name="Cafe", currency="ARS", **kw):
    data = dict(
        user_id=user_id,
        amount=Decimal(str(amount)),
        type=type,
        currency=currency,
        transaction_date=day,
        product_name=name,
        account_type="cash",
        payment_method="cash",
    )
    data.update(kw)
    return Transaction(**data)


async def _seed(db, user):
    db.add_all(
        [
            _tx(user.id, 100, name="A"),
            _tx(user.id, 200, name="B"),
            _tx(user.id, 300, name="C", day="2026-10-20"),
            _tx(user.id, 1000, type="income", name="Sueldo", day="2026-10-01"),
        ]
    )
    await db.commit()


def _wb(resp):
    return load_workbook(io.BytesIO(resp.content))


def _rows(ws):
    return [list(r) for r in ws.iter_rows(values_only=True)]


def _pdf_text(resp):
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(resp.content))
    return reader, "\n".join(p.extract_text() for p in reader.pages)


async def test_xlsx_headers_de_la_respuesta(api_auth_client, db_session, test_user):
    await _seed(db_session, test_user)
    r = await api_auth_client.get(URL, params={"format": "xlsx", **RANGE})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith(XLSX)
    assert r.headers["cache-control"] == "no-store"
    assert (
        r.headers["content-disposition"]
        == 'attachment; filename="cancen-finanzas-2026-10-01_2026-10-31.xlsx"'
    )
    assert int(r.headers["content-length"]) == len(r.content)
    assert r.content[:2] == b"PK"


async def test_xlsx_rango_por_defecto_es_el_mes_en_curso(api_auth_client, db_session, test_user):
    hoy = date.today()
    db_session.add_all(
        [
            _tx(test_user.id, 10, name="de-este-mes", day=hoy.replace(day=1).isoformat()),
            _tx(test_user.id, 20, name="viejo", day="2020-01-15"),
        ]
    )
    await db_session.commit()
    # tz -180 puede correr "hoy" un dia: mismo mes salvo el primer dia; se acepta ambos meses.
    r = await api_auth_client.get(URL, params={"format": "xlsx", "tz_offset_minutes": 0})
    rows = _rows(_wb(r)["Movimientos"])
    nombres = [x[rows[0].index("Descripción")] for x in rows[1:]]
    assert nombres == ["de-este-mes"]


async def test_xlsx_hojas_numeros_y_fechas(api_auth_client, db_session, test_user):
    await _seed(db_session, test_user)
    r = await api_auth_client.get(URL, params={"format": "xlsx", **RANGE})
    wb = _wb(r)
    assert wb.sheetnames == ["Resumen", "Movimientos", "Por categoría", "Por mes"]
    assert wb.properties.creator == "Can_cen"
    mov = wb["Movimientos"]
    rows = _rows(mov)
    header = rows[0]
    assert header[0] == "Fecha"
    col = header.index("Monto")
    amounts = [row[col] for row in rows[1:]]
    # Orden por fecha: ingreso del 1, egresos del 5 y del 20; egresos negativos.
    assert amounts == [1000, -100, -200, -300]
    assert all(isinstance(a, (int, float)) for a in amounts)
    assert isinstance(rows[1][0], datetime) and rows[1][0].date() == date(2026, 10, 1)
    assert mov["A2"].number_format == "DD/MM/YYYY"
    assert mov.freeze_panes == "A2"


async def test_xlsx_totales_cuadran_con_el_detalle(api_auth_client, db_session, test_user):
    await _seed(db_session, test_user)
    r = await api_auth_client.get(URL, params={"format": "xlsx", **RANGE})
    wb = _wb(r)
    fila = next(x for x in _rows(wb["Resumen"]) if x and x[0] == "ARS")
    # Moneda, Ingresos, Egresos, Balance, Movimientos
    assert fila[1:5] == [1000, 600, 400, 4]
    por_mes = _rows(wb["Por mes"])
    assert por_mes[1][:5] == ["2026-10", "ARS", 1000, 600, 400]
    por_cat = _rows(wb["Por categoría"])
    assert por_cat[1][:5] == ["Sin categoría", "ARS", 1000, 600, 4]


async def test_xlsx_no_suma_monedas_distintas(api_auth_client, db_session, test_user):
    db_session.add_all(
        [_tx(test_user.id, 100), _tx(test_user.id, 50, currency="USD", type="income")]
    )
    await db_session.commit()
    r = await api_auth_client.get(URL, params={"format": "xlsx", **RANGE})
    resumen = _rows(_wb(r)["Resumen"])
    assert [x[0] for x in resumen if x and x[0] in ("ARS", "USD")] == ["ARS", "USD"]
    assert not any(x and str(x[0]).lower() == "total" for x in resumen)


@pytest.mark.parametrize("texto", ['=HYPERLINK("http://x","clic")', "+1", "-2+3", "@SUM(A1)"])
async def test_xlsx_escapa_formulas_y_no_hay_celdas_formula(
    api_auth_client, db_session, test_user, texto
):
    cat = Category(user_id=test_user.id, name=texto)
    db_session.add(cat)
    await db_session.flush()
    db_session.add(
        _tx(test_user.id, 150, name=texto, merchant_name=texto, notes=texto, category_id=cat.id)
    )
    await db_session.commit()
    r = await api_auth_client.get(URL, params={"format": "xlsx", **RANGE})
    wb = _wb(r)
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                assert c.data_type != "f", (ws.title, c.coordinate, c.value)
    mov = _rows(wb["Movimientos"])
    header, fila = mov[0], mov[1]
    for col in ("Descripción", "Comercio", "Categoría", "Notas"):
        assert fila[header.index(col)] == "'" + texto
    # El monto negativo sigue siendo un numero, no un string escapado.
    assert fila[header.index("Monto")] == -150


async def test_xlsx_filtros_tipo_categoria_y_sin_categoria(api_auth_client, db_session, test_user):
    cat = Category(user_id=test_user.id, name="Comida")
    db_session.add(cat)
    await db_session.flush()
    db_session.add_all(
        [
            _tx(test_user.id, 10, name="con", category_id=cat.id),
            _tx(test_user.id, 20, name="sin"),
            _tx(test_user.id, 30, name="ing", type="income"),
        ]
    )
    await db_session.commit()
    base = {"format": "xlsx", **RANGE}

    def names(resp):
        rows = _rows(_wb(resp)["Movimientos"])
        i = rows[0].index("Descripción")
        return [x[i] for x in rows[1:]]

    assert names(await api_auth_client.get(URL, params={**base, "type": "income"})) == ["ing"]
    assert names(await api_auth_client.get(URL, params={**base, "category_id": cat.id})) == ["con"]
    r = await api_auth_client.get(URL, params={**base, "category_id": "none", "type": "expense"})
    assert names(r) == ["sin"]


async def test_xlsx_filtro_por_cuenta(api_auth_client, db_session, test_user):
    acc = BankAccount(
        user_id=test_user.id, name="MP", bank_name="Mercado Pago",
        account_type="checking", last4="1234",
    )
    db_session.add(acc)
    await db_session.flush()
    db_session.add_all(
        [
            _tx(test_user.id, 10, name="mp", bank_entity_name="Mercado Pago",
                account_type="checking", account_last4="1234"),
            _tx(test_user.id, 20, name="otro", bank_entity_name="Galicia",
                account_type="checking", account_last4="9999"),
        ]
    )
    await db_session.commit()
    r = await api_auth_client.get(URL, params={"format": "xlsx", **RANGE, "account_id": acc.id})
    rows = _rows(_wb(r)["Movimientos"])
    assert [x[rows[0].index("Descripción")] for x in rows[1:]] == ["mp"]


async def test_xlsx_ignora_movimientos_borrados(api_auth_client, db_session, test_user):
    db_session.add_all(
        [_tx(test_user.id, 10, name="vivo"), _tx(test_user.id, 99, name="borrado", is_deleted=True)]
    )
    await db_session.commit()
    r = await api_auth_client.get(URL, params={"format": "xlsx", **RANGE})
    assert len(_rows(_wb(r)["Movimientos"])) == 2


async def test_xlsx_nombre_del_lote_importado(api_auth_client, db_session, test_user):
    from app.modules.finanzas.transfer.models import ImportBatch

    b = ImportBatch(
        user_id=test_user.id, status="confirmed", preset="generic", filename="=cmd.csv",
        file_sha256="0" * 64, header_signature="0" * 64, mapping={},
    )
    db_session.add(b)
    await db_session.flush()
    db_session.add(_tx(test_user.id, 10, import_batch_id=b.id))
    await db_session.commit()
    r = await api_auth_client.get(URL, params={"format": "xlsx", **RANGE})
    rows = _rows(_wb(r)["Movimientos"])
    assert rows[1][rows[0].index("Importado")] == "'=cmd.csv"


async def test_inversiones_cotizaciones_y_recurrentes_solo_si_se_piden(
    api_auth_client, db_session, test_user
):
    db_session.add(_tx(test_user.id, 10))
    db_session.add(
        Investment(
            user_id=test_user.id, asset_type="fixed_term", name="PF Galicia", currency="ARS",
            invested_amount=Decimal("1000"), status="active",
        )
    )
    db_session.add(
        RecurringTransaction(
            user_id=test_user.id, type="expense", name="Alquiler", amount=Decimal("500"),
            currency="ARS", frequency="monthly", interval_count=1, day_of_month=5,
            start_date=date(2026, 1, 5), anchor_date=date(2026, 1, 5),
            next_occurrence_date=date(2026, 11, 5), status="active",
        )
    )
    await db_session.commit()
    base = {"format": "xlsx", **RANGE}
    r = await api_auth_client.get(URL, params=base)
    assert _wb(r).sheetnames == ["Resumen", "Movimientos", "Por categoría", "Por mes"]
    r = await api_auth_client.get(URL, params={**base, "include_investments": "true"})
    wb = _wb(r)
    assert wb.sheetnames == [
        "Resumen", "Movimientos", "Por categoría", "Por mes", "Inversiones", "Recurrentes",
    ]
    inv = [c for row in _rows(wb["Inversiones"]) for c in row]
    assert "PF Galicia" in inv and "Cotizaciones" in inv
    rec = [c for row in _rows(wb["Recurrentes"]) for c in row]
    assert "Alquiler" in rec


async def test_pdf_valido_formato_es_ar_y_emoji_sin_fallar(api_auth_client, db_session, test_user):
    db_session.add(_tx(test_user.id, Decimal("1234.50"), name="Pizza 🍕 grande"))
    await db_session.commit()
    r = await api_auth_client.get(URL, params={"format": "pdf", **RANGE})
    assert r.status_code == 200, r.text
    assert r.content.startswith(b"%PDF")
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"].endswith('_2026-10-31.pdf"')
    reader, text = _pdf_text(r)
    assert "$ 1.234,50" in text
    assert "Can_cen" in text
    assert "Pizza" in text
    assert "01/10/2026" in text


async def test_pdf_varias_paginas_con_numeracion(api_auth_client, db_session, test_user):
    db_session.add_all(
        [_tx(test_user.id, 10 + i, name=f"Movimiento {i}", day=f"2026-10-{1 + i % 28:02d}") for i in range(180)]
    )
    await db_session.commit()
    r = await api_auth_client.get(URL, params={"format": "pdf", **RANGE})
    reader, text = _pdf_text(r)
    n = len(reader.pages)
    assert n >= 3
    assert f"Página {n} de {n}" in text
    assert "Página 1 de" in text


async def test_pdf_con_inversiones(api_auth_client, db_session, test_user):
    db_session.add(_tx(test_user.id, 10))
    db_session.add(
        Investment(
            user_id=test_user.id, asset_type="fixed_term", name="PF Galicia", currency="ARS",
            invested_amount=Decimal("1000"), status="active",
        )
    )
    await db_session.commit()
    r = await api_auth_client.get(URL, params={"format": "pdf", **RANGE, "include_investments": "true"})
    _, text = _pdf_text(r)
    assert "PF Galicia" in text and "Patrimonio" in text


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"format": "csv"},
        {"format": "xlsx", "date_from": "2026-10-10", "date_to": "2026-10-01"},
        {"format": "xlsx", "date_from": "2015-01-01", "date_to": "2026-10-01"},
        {"format": "xlsx", "type": "transfer"},
    ],
)
async def test_parametros_invalidos_dan_422(api_auth_client, params):
    r = await api_auth_client.get(URL, params=params)
    assert r.status_code == 422, r.text


async def test_tope_de_filas_dev_422_sin_generar(api_auth_client, db_session, test_user, monkeypatch):
    monkeypatch.setattr(settings, "FINANCE_EXPORT_MAX_ROWS_PDF", 2)
    monkeypatch.setattr(settings, "FINANCE_EXPORT_MAX_ROWS_XLSX", 3)
    db_session.add_all([_tx(test_user.id, 10 + i, name=f"m{i}") for i in range(4)])
    await db_session.commit()
    r = await api_auth_client.get(URL, params={"format": "pdf", **RANGE})
    assert r.status_code == 422
    assert "4 movimientos" in r.json()["detail"] and "PDF" in r.json()["detail"]
    r = await api_auth_client.get(URL, params={"format": "xlsx", **RANGE})
    assert r.status_code == 422
    r = await api_auth_client.get(
        URL, params={"format": "xlsx", "date_from": "2026-10-20", "date_to": "2026-10-31"}
    )
    assert r.status_code == 200  # el tope cuenta los movimientos del rango


async def test_export_requiere_autenticacion(client):
    r = await client.get(URL, params={"format": "xlsx"})
    assert r.status_code == 401


async def test_rate_limit_429_con_retry_after(api_auth_client, db_session, test_user, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    ultimo = None
    for _ in range(11):
        ultimo = await api_auth_client.get(URL, params={"format": "xlsx", **RANGE})
    assert ultimo.status_code == 429
    assert "retry-after" in ultimo.headers


# ── Aislamiento entre usuarios ──────────────────────────────────────────────


async def _otro_usuario(email="otro@test.com"):
    transport = ASGITransport(app=app)
    ac = AsyncClient(transport=transport, base_url="http://test")
    r = await ac.post(
        "/auth/api/register",
        json={
            "email": email, "full_name": "Otro", "password": "testpass123",
            "accept_terms": True, "confirm_age": True,
        },
    )
    assert r.status_code == 201, r.text
    return ac


async def test_export_no_incluye_datos_de_otro_usuario(api_auth_client, db_session, test_user):
    db_session.add(_tx(test_user.id, 10, name="mio"))
    await db_session.commit()
    otro = await _otro_usuario()
    try:
        cat = await otro.post("/api/v1/finance/categories", json={"name": "Ajena"})
        await otro.post(
            "/api/v1/finance/transactions",
            json={
                "amount": "77.00", "type": "expense", "transaction_date": "2026-10-05",
                "account_type": "cash", "payment_method": "cash", "product_name": "secreto",
                "category_id": cat.json()["id"],
            },
        )
        cat_ajena = cat.json()["id"]
    finally:
        await otro.aclose()
    r = await api_auth_client.get(URL, params={"format": "xlsx", **RANGE})
    celdas = [c for ws in _wb(r).worksheets for row in ws.iter_rows(values_only=True) for c in row]
    assert "mio" in celdas and "secreto" not in celdas and "Ajena" not in celdas
    # Categoria o cuenta ajena: 404, nunca datos.
    r = await api_auth_client.get(URL, params={"format": "xlsx", **RANGE, "category_id": cat_ajena})
    assert r.status_code == 404

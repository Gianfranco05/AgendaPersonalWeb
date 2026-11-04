import io
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook
from sqlalchemy import select

from app.config import settings
from app.main import app
from app.modules.finanzas.models import BankAccount, Category, Transaction
from app.modules.finanzas.enums import AccountType, PaymentMethod
from app.modules.finanzas.transfer.models import ImportBatch

pytestmark = pytest.mark.asyncio

FIX = Path(__file__).parent / "fixtures" / "finanzas_import"
BASE = "/api/v1/finance/imports"


def _file(name):
    return (FIX / name).read_bytes()


async def _preview(c, content, filename="movs.csv", **data):
    if isinstance(content, str):
        filename, content = content, _file(content)
    data.setdefault("tz_offset_minutes", "-180")
    return await c.post(
        f"{BASE}/preview", files={"file": (filename, content, "application/octet-stream")}, data=data
    )


def _rows(p, status=None):
    return [r for r in p["rows"] if status is None or r["status"] == status]


def _all_ok(p, **over):
    return {"rows": [{"index": r["index"], "include": True, **over} for r in _rows(p, "ok")]}


async def _import(c, name, **data):
    r = await _preview(c, name, **data)
    assert r.status_code == 201, r.text
    p = r.json()
    r = await c.post(f"{BASE}/{p['batch_id']}/confirm", json=_all_ok(p))
    assert r.status_code == 200, r.text
    return p, r.json()


async def _txs(db, user_id, **filters):
    q = select(Transaction).where(Transaction.user_id == user_id)
    for k, v in filters.items():
        q = q.where(getattr(Transaction, k) == v)
    return (await db.execute(q.order_by(Transaction.transaction_date, Transaction.product_name))).scalars().all()


async def _otro(email="otro@test.com"):
    ac = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    r = await ac.post(
        "/auth/api/register",
        json={"email": email, "full_name": "Otro", "password": "testpass123",
              "accept_terms": True, "confirm_age": True},
    )
    assert r.status_code == 201, r.text
    return ac


# ── Presets y preview ───────────────────────────────────────────────────────


async def test_presets(api_auth_client):
    r = await api_auth_client.get(f"{BASE}/presets")
    assert r.status_code == 200
    assert [p["key"] for p in r.json()] == ["mercadopago_release", "mercadopago_account_money", "generic"]


async def test_preview_mercadopago_disponible_en_ingles(api_auth_client):
    r = await _preview(api_auth_client, "mp_release_en.csv")
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["preset"] == p["detected_preset"] == "mercadopago_release"
    assert p["mapping_source"] == "preset" and p["mapping_complete"] is True
    assert p["counts"]["ok"] == 3 and p["counts"]["skipped"] == 2
    ok = _rows(p, "ok")
    # 10:15:30 en GMT-4 = 11:15:30 en Argentina (UTC-3).
    assert (ok[0]["date"], ok[0]["time"], ok[0]["type"], ok[0]["amount"]) == (
        "2026-10-02", "11:15:30", "income", "2500.50",
    )
    assert ok[0]["description"] == "Cobro · REF-A" and ok[0]["currency"] == "ARS"
    # 23:30 GMT-4 del 3 = 00:30 del 4 en Argentina.
    assert (ok[1]["date"], ok[1]["type"], ok[1]["amount"], ok[1]["description"]) == (
        "2026-10-04", "expense", "1000.00", "Retiro",
    )
    assert ok[2]["description"] == "Impuesto / retención" and ok[2]["amount"] == "15.25"
    assert p["totals_by_currency"] == [
        {"currency": "ARS", "income": "2500.50", "expense": "1015.25", "count": 3}
    ]
    assert [r["status"] for r in p["rows"]].count("skipped") == 2
    assert "informativa" in _rows(p, "skipped")[0]["errors"][0]


async def test_preview_mercadopago_punto_y_coma_bom_decimales_es_ar(api_auth_client):
    p = (await _preview(api_auth_client, "mp_release_es_punto_y_coma.csv")).json()
    assert p["preset"] == "mercadopago_release"
    ok = _rows(p, "ok")
    assert [(r["type"], r["amount"], r["description"]) for r in ok] == [
        ("income", "1234.56", "Cobro"), ("expense", "200.00", "Devolución"),
    ]


async def test_preview_mercadopago_dinero_en_cuenta_con_respaldo_de_monto(api_auth_client):
    p = (await _preview(api_auth_client, "mp_account_money.csv")).json()
    assert p["preset"] == "mercadopago_account_money"
    ok = _rows(p, "ok")
    assert [(r["type"], r["amount"], r["description"]) for r in ok] == [
        ("income", "4800.00", "Cobro · Venta remera"),
        ("expense", "3000.00", "Retiro · Retiro a CBU"),
        ("expense", "500.00", "Devolución · Devolucion"),  # SETTLEMENT_NET_AMOUNT vacio
    ]


async def test_preview_generico_cp1252_con_preambulo(api_auth_client):
    p = (await _preview(api_auth_client, "banco_generico_cp1252.csv")).json()
    assert p["preset"] == "generic" and p["mapping_source"] == "heuristic"
    assert p["header_row"] == 2 and p["headers"][2] == "Débito"
    ok = _rows(p, "ok")
    assert [(r["date"], r["type"], r["amount"]) for r in ok] == [
        ("2026-10-01", "expense", "1234.56"),
        ("2026-10-02", "income", "250000.00"),
        ("2026-10-13", "expense", "8500.00"),
    ]
    assert ok[1]["description"] == "Acreditación sueldo"
    assert ok[0]["merchant_category"] == "grocery"


async def test_preview_xlsx_monto_con_signo_y_monedas(api_auth_client):
    p = (await _preview(api_auth_client, "billetera_monto_signo.xlsx")).json()
    ok = _rows(p, "ok")
    assert [(r["type"], r["amount"], r["currency"]) for r in ok] == [
        ("expense", "4321.50", "ARS"), ("income", "300000.00", "ARS"), ("expense", "100.00", "USD"),
    ]
    assert ok[0]["date"] == "2026-10-03" and ok[0]["time"] == "14:05:00"
    assert {t["currency"] for t in p["totals_by_currency"]} == {"ARS", "USD"}


async def test_filas_con_error_se_explican_y_el_tope_de_monto_se_respeta(api_auth_client):
    csv = (
        "fecha,descripcion,monto\n"
        "2026-10-01,ok,-10\n"
        "no-fecha,mala,-10\n"
        "2026-10-02,gigante,\"10.000.000.000,00\"\n"
        "2026-10-03,vacio,0\n"
        "2026-10-04,letras,abc\n"
    ).encode()
    p = (await _preview(api_auth_client, csv)).json()
    assert p["counts"] == {"ok": 1, "error": 3, "duplicate": 0, "possible_duplicate": 0, "skipped": 1}
    errs = {r["description"]: r["errors"] for r in p["rows"] if r["status"] == "error"}
    assert any("fecha" in e for e in errs["mala"])
    assert any("fuera de rango" in e for e in errs["gigante"])
    assert any("monto" in e for e in errs["letras"])


async def test_mapeo_incompleto_devuelve_el_preview_para_mapear(api_auth_client):
    p = (await _preview(api_auth_client, b"col1,col2\nx,y\n")).json()
    assert p["mapping_complete"] is False and p["rows"] == []
    assert p["headers"] == ["col1", "col2"] and p["sample_rows"] == [["x", "y"]]


async def test_fecha_ambigua_avisa_y_mes_primero_se_detecta(api_auth_client):
    amb = b"fecha,descripcion,monto\n01/02/2026,a,-1\n03/04/2026,b,-1\n"
    p = (await _preview(api_auth_client, amb)).json()
    assert _rows(p)[0]["date"] == "2026-02-01"
    assert any("ambigu" in w for w in p["warnings"])
    mf = b"fecha,descripcion,monto\n01/13/2026,a,-1\n02/01/2026,b,-1\n"
    p = (await _preview(api_auth_client, mf)).json()
    assert [r["date"] for r in _rows(p)] == ["2026-01-13", "2026-02-01"]


# ── Errores de subida ───────────────────────────────────────────────────────


async def test_subida_invalida_415_413_422(api_auth_client, monkeypatch):
    r = await _preview(api_auth_client, b"%PDF-1.4\n\x00\x00", "x.pdf")
    assert r.status_code == 415
    r = await _preview(api_auth_client, b"\xd0\xcf\x11\xe0" + b"x" * 100, "viejo.xls")
    assert r.status_code == 415 and ".xlsx" in r.json()["detail"]
    r = await _preview(api_auth_client, b"", "vacio.csv")
    assert r.status_code == 422
    monkeypatch.setattr(settings, "FINANCE_IMPORT_MAX_BYTES", 100)
    r = await _preview(api_auth_client, b"a,b\n" + b"1,2\n" * 100, "grande.csv")
    assert r.status_code == 413


async def test_tope_de_body_de_la_subida_es_mayor_al_global_pero_acotado(api_auth_client):
    # 1,5 MiB: pasa el middleware (2 MiB + overhead) aunque el global es 1 MiB.
    body = b"fecha,descripcion,monto\n" + (b"2026-10-01,x,-1\n" * 3)
    pad = b"#" * (1_500_000)
    r = await _preview(api_auth_client, body + pad, "grande.csv")
    assert r.status_code != 413
    # Con Content-Length declarado mayor al tope: lo corta el middleware.
    r = await api_auth_client.post(
        f"{BASE}/preview",
        headers={"content-length": str(5 * 1024 * 1024)},
        files={"file": ("a.csv", b"x", "text/csv")},
    )
    assert r.status_code == 413


async def test_requiere_autenticacion(client):
    assert (await client.get(f"{BASE}/presets")).status_code == 401
    assert (await client.get(BASE)).status_code == 401
    r = await client.post(f"{BASE}/preview", files={"file": ("a.csv", b"a", "text/csv")})
    assert r.status_code == 401


# ── Confirmar ───────────────────────────────────────────────────────────────


async def test_confirmar_crea_movimientos_validos_con_lote(api_auth_client, db_session, test_user):
    p, out = await _import(api_auth_client, "mp_release_en.csv")
    assert out["status"] == "confirmed" and out["imported_count"] == 3
    assert out["skipped_count"] == 2 and out["row_count"] == 5
    txs = await _txs(db_session, test_user.id)
    assert len(txs) == 3
    for t in txs:
        assert t.import_batch_id == p["batch_id"] and t.import_row_hash
        assert t.payment_method == "transfer" and t.payment_method in PaymentMethod._value2member_map_
        assert t.account_type in AccountType._value2member_map_
        assert t.is_recurring is False and t.recurring_parent_id is None
        assert t.bank_entity_name == "Mercado Pago"
        assert isinstance(Decimal(str(t.amount)), Decimal)
    by_amount = {Decimal(str(t.amount)): t for t in txs}
    assert by_amount[Decimal("2500.50")].type == "income"
    assert by_amount[Decimal("1000.00")].transaction_date == "2026-10-04"
    assert by_amount[Decimal("1000.00")].transaction_time == "00:30:00"
    # El API de movimientos los lista con el id del lote.
    r = await api_auth_client.get("/api/v1/finance/transactions", params={"limit": 50})
    assert {i["import_batch_id"] for i in r.json()["items"]} == {p["batch_id"]}


async def test_generico_usa_other_y_cuenta_destino(api_auth_client, db_session, test_user):
    acc = BankAccount(user_id=test_user.id, name="Galicia CC", bank_name="Galicia",
                      account_type="checking", last4="4321", currency="ARS")
    db_session.add(acc)
    await db_session.commit()
    p, _ = await _import(api_auth_client, "banco_generico_cp1252.csv", account_id=acc.id)
    assert p["account_id"] == acc.id
    for t in await _txs(db_session, test_user.id):
        assert (t.payment_method, t.bank_entity_name, t.account_type, t.account_last4) == (
            "other", "Galicia", "checking", "4321",
        )
    # Lo importado a una cuenta se exporta filtrando por esa cuenta.
    r = await api_auth_client.get(
        "/api/v1/finance/export",
        params={"format": "xlsx", "date_from": "2026-10-01", "date_to": "2026-10-31", "account_id": acc.id},
    )
    from openpyxl import load_workbook
    ws = load_workbook(io.BytesIO(r.content))["Movimientos"]
    assert len(list(ws.iter_rows())) == 4


async def test_confirmar_respeta_exclusiones_y_overrides(api_auth_client, db_session, test_user):
    cat = Category(user_id=test_user.id, name="Varios")
    db_session.add(cat)
    await db_session.commit()
    p = (await _preview(api_auth_client, "banco_generico_cp1252.csv")).json()
    rows = _rows(p, "ok")
    body = {"rows": [
        {"index": rows[0]["index"], "include": False},
        {"index": rows[1]["index"], "include": True, "category_id": cat.id, "type": "expense",
         "description": "Sueldo corregido"},
        {"index": rows[2]["index"], "include": True},
    ]}
    out = (await api_auth_client.post(f"{BASE}/{p['batch_id']}/confirm", json=body)).json()
    assert out["imported_count"] == 2
    txs = await _txs(db_session, test_user.id)
    assert sorted(t.product_name for t in txs) == ["Pago servicio Edenor", "Sueldo corregido"]
    t = next(t for t in txs if t.product_name == "Sueldo corregido")
    assert t.category_id == cat.id and t.type == "expense" and Decimal(str(t.amount)) == Decimal("250000.00")


async def test_confirmar_incluir_error_o_duplicado_da_422(api_auth_client):
    csv = b"fecha,descripcion,monto\n2026-10-01,ok,-10\nmala,x,-5\n"
    p = (await _preview(api_auth_client, csv)).json()
    bad = _rows(p, "error")[0]["index"]
    r = await api_auth_client.post(f"{BASE}/{p['batch_id']}/confirm",
                                   json={"rows": [{"index": bad, "include": True}]})
    assert r.status_code == 422
    r = await api_auth_client.post(f"{BASE}/{p['batch_id']}/confirm",
                                   json={"rows": [{"index": 999, "include": True}]})
    assert r.status_code == 422


async def test_confirmar_dos_veces_da_409(api_auth_client):
    p, _ = await _import(api_auth_client, "mp_release_en.csv")
    r = await api_auth_client.post(f"{BASE}/{p['batch_id']}/confirm", json=_all_ok(p))
    assert r.status_code == 409


async def test_preview_vencido_da_410(api_auth_client, db_session):
    p = (await _preview(api_auth_client, "mp_release_en.csv")).json()
    batch = await db_session.get(ImportBatch, p["batch_id"])
    batch.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.commit()
    r = await api_auth_client.post(f"{BASE}/{p['batch_id']}/confirm", json=_all_ok(p))
    assert r.status_code == 410 and "venció" in r.json()["detail"]
    r = await api_auth_client.put(f"{BASE}/{p['batch_id']}/mapping", json={"header_row": 0})
    assert r.status_code == 410


async def test_raw_table_se_borra_al_confirmar(api_auth_client, db_session):
    p, _ = await _import(api_auth_client, "mp_release_en.csv")
    batch = await db_session.get(ImportBatch, p["batch_id"])
    await db_session.refresh(batch)
    assert batch.raw_table is None and batch.status == "confirmed" and batch.confirmed_at


# ── Duplicados ──────────────────────────────────────────────────────────────


async def test_resubir_el_mismo_archivo_marca_todo_como_ya_importado(api_auth_client):
    await _import(api_auth_client, "mp_release_en.csv")
    p = (await _preview(api_auth_client, "mp_release_en.csv")).json()
    assert p["counts"]["duplicate"] == 3 and p["counts"]["ok"] == 0
    d = _rows(p, "duplicate")[0]
    assert d["duplicate_of"]["id"] and d["duplicate_of"]["date"]
    assert any("Ya importaste este archivo" in w for w in p["warnings"])
    r = await api_auth_client.post(
        f"{BASE}/{p['batch_id']}/confirm", json={"rows": [{"index": d["index"], "include": True}]}
    )
    assert r.status_code == 422


async def test_dos_filas_identicas_en_un_archivo_son_dos_movimientos(api_auth_client, db_session, test_user):
    csv = b"fecha,descripcion,monto\n2026-10-01,Cafe,-100\n2026-10-01,Cafe,-100\n"
    p, out = await _import(api_auth_client, csv)
    assert out["imported_count"] == 2
    assert len({r["row_hash"] for r in p["rows"]}) == 2
    p2 = (await _preview(api_auth_client, csv)).json()
    assert p2["counts"]["duplicate"] == 2


async def test_archivo_que_se_superpone_solo_trae_lo_nuevo(api_auth_client):
    await _import(api_auth_client, b"fecha,descripcion,monto\n2026-10-01,Cafe,-100\n2026-10-02,Taxi,-300\n", )
    p = (await _preview(
        api_auth_client,
        b"fecha,descripcion,monto\n2026-10-02,Taxi,-300\n2026-10-03,Libro,-900\n",
    )).json()
    assert [(r["description"], r["status"]) for r in p["rows"]] == [("Taxi", "duplicate"), ("Libro", "ok")]


async def test_posible_duplicado_contra_un_movimiento_manual(api_auth_client, db_session, test_user):
    db_session.add(Transaction(
        user_id=test_user.id, amount=Decimal("1234.56"), type="expense", currency="ARS",
        transaction_date="2026-10-02", product_name="Compra Coto", account_type="cash",
        payment_method="cash",
    ))
    await db_session.commit()
    p = (await _preview(api_auth_client, "banco_generico_cp1252.csv")).json()
    posible = _rows(p, "possible_duplicate")
    assert [r["description"] for r in posible] == ["COMPRA COTO SUC 12"]  # un dia de diferencia
    assert posible[0]["duplicate_of"]["description"] == "Compra Coto"
    assert p["counts"]["possible_duplicate"] == 1 and p["counts"]["ok"] == 2
    # Viene destildado por defecto en `_all_ok`; el usuario puede incluirlo.
    out = (await api_auth_client.post(
        f"{BASE}/{p['batch_id']}/confirm",
        json={"rows": [{"index": posible[0]["index"], "include": True}]},
    )).json()
    assert out["imported_count"] == 1


async def test_movimiento_borrado_no_cuenta_como_duplicado(api_auth_client, db_session, test_user):
    p, _ = await _import(api_auth_client, "mp_release_en.csv")
    for t in await _txs(db_session, test_user.id):
        t.is_deleted = True
    await db_session.commit()
    p2 = (await _preview(api_auth_client, "mp_release_en.csv")).json()
    assert p2["counts"]["ok"] == 3 and p2["counts"]["duplicate"] == 0


# ── Remapear ────────────────────────────────────────────────────────────────


async def test_remap_cambia_el_mapeo_sin_resubir(api_auth_client):
    p = (await _preview(api_auth_client, "banco_generico_cp1252.csv")).json()
    m = p["mapping"]
    m["invert_sign"] = True
    r = await api_auth_client.put(f"{BASE}/{p['batch_id']}/mapping", json={"mapping": m})
    assert r.status_code == 200, r.text
    q = r.json()
    assert q["mapping_source"] == "user"
    assert [x["type"] for x in _rows(q, "ok")] == ["income", "expense", "income"]


async def test_remap_header_row_y_formato_de_fecha(api_auth_client):
    csv = b"Titulo del banco\nfecha,descripcion,monto\n01/02/2026,a,-1\n"
    p = (await _preview(api_auth_client, csv)).json()
    r = await api_auth_client.put(f"{BASE}/{p['batch_id']}/mapping", json={"header_row": 1})
    assert r.status_code == 200
    m = r.json()["mapping"]
    m["date_format"] = "mm/dd/yyyy"
    q = (await api_auth_client.put(f"{BASE}/{p['batch_id']}/mapping", json={"mapping": m})).json()
    assert _rows(q, "ok")[0]["date"] == "2026-01-02"


async def test_remap_con_columna_fuera_de_rango_da_422(api_auth_client):
    p = (await _preview(api_auth_client, "banco_generico_cp1252.csv")).json()
    m = p["mapping"]
    m["amount"] = 40
    r = await api_auth_client.put(f"{BASE}/{p['batch_id']}/mapping", json={"mapping": m})
    assert r.status_code == 422


async def test_remap_de_un_lote_confirmado_da_409(api_auth_client):
    p, _ = await _import(api_auth_client, "mp_release_en.csv")
    r = await api_auth_client.put(f"{BASE}/{p['batch_id']}/mapping", json={"header_row": 0})
    assert r.status_code == 409


async def test_forzar_preset_que_no_matchea_da_422(api_auth_client):
    p = (await _preview(api_auth_client, "banco_generico_cp1252.csv")).json()
    r = await api_auth_client.put(f"{BASE}/{p['batch_id']}/mapping", json={"preset": "mercadopago_release"})
    assert r.status_code == 422
    r = await _preview(api_auth_client, "banco_generico_cp1252.csv", preset="inventado")
    assert r.status_code == 422


# ── Mapeo recordado ─────────────────────────────────────────────────────────


async def test_mapeo_recordado_por_firma_de_encabezados_y_por_usuario(api_auth_client):
    csv1 = b"dia,que,cuanto\n01/10/2026,Cafe,-100\n"
    p = (await _preview(api_auth_client, csv1)).json()
    assert p["mapping_complete"] is False
    m = {"date": 0, "description": [1], "amount_mode": "signed", "amount": 2, "date_format": "dd/mm/yyyy"}
    q = (await api_auth_client.put(f"{BASE}/{p['batch_id']}/mapping", json={"mapping": m})).json()
    assert q["mapping_complete"] and q["counts"]["ok"] == 1
    await api_auth_client.post(f"{BASE}/{p['batch_id']}/confirm", json=_all_ok(q))

    csv2 = b"dia,que,cuanto\n05/10/2026,Taxi,-300\n"
    p2 = (await _preview(api_auth_client, csv2)).json()
    assert p2["mapping_source"] == "remembered" and p2["counts"]["ok"] == 1
    assert any("mapeo de tu importación" in w for w in p2["warnings"])

    otro = await _otro()
    try:
        p3 = (await _preview(otro, csv2)).json()
        assert p3["mapping_source"] != "remembered" and p3["mapping_complete"] is False
    finally:
        await otro.aclose()


# ── Categorias sugeridas ────────────────────────────────────────────────────


async def test_sugerencia_por_historial_y_por_regla(api_auth_client, db_session, test_user):
    comida = Category(user_id=test_user.id, name="Supermercado")
    ocio = Category(user_id=test_user.id, name="Entretenimiento")
    db_session.add_all([comida, ocio])
    await db_session.flush()
    db_session.add(Transaction(
        user_id=test_user.id, amount=Decimal("50"), type="expense", currency="ARS",
        transaction_date=date.today().isoformat(), product_name="Panaderia La Esquina 123",
        account_type="cash", payment_method="cash", category_id=ocio.id,
    ))
    await db_session.commit()
    csv = (
        "fecha,descripcion,monto\n"
        "2026-10-01,PANADERIA LA ESQUINA 456,-10\n"   # historial exacto (sin digitos)
        "2026-10-02,Compra Coto Sucursal 9,-20\n"      # regla -> grocery -> Supermercado
        "2026-10-03,Algo desconocido,-30\n"
    ).encode()
    p = (await _preview(api_auth_client, csv)).json()
    r = _rows(p)
    assert (r[0]["suggested_category_id"], r[0]["suggestion_source"]) == (ocio.id, "history")
    assert (r[1]["suggested_category_id"], r[1]["suggestion_source"]) == (comida.id, "rule")
    assert (r[2]["suggested_category_id"], r[2]["suggestion_source"]) == (None, "none")
    # Confirmar sin categoria usa la sugerida; "" la deja sin categoria.
    body = {"rows": [
        {"index": r[0]["index"], "include": True},
        {"index": r[1]["index"], "include": True, "category_id": ""},
    ]}
    await api_auth_client.post(f"{BASE}/{p['batch_id']}/confirm", json=body)
    txs = {t.product_name: t for t in await _txs(db_session, test_user.id) if t.import_batch_id}
    assert txs["PANADERIA LA ESQUINA 456"].category_id == ocio.id
    assert txs["Compra Coto Sucursal 9"].category_id is None
    assert txs["Compra Coto Sucursal 9"].merchant_category == "grocery"


# ── Deshacer ────────────────────────────────────────────────────────────────


async def test_deshacer_borra_el_lote_y_deja_reimportar(api_auth_client, db_session, test_user):
    db_session.add(Transaction(
        user_id=test_user.id, amount=Decimal("100"), type="income", currency="ARS",
        transaction_date="2026-09-01", product_name="Manual", account_type="cash", payment_method="cash",
    ))
    await db_session.commit()
    s0 = (await api_auth_client.get("/api/v1/finance/summary")).json()
    p, _ = await _import(api_auth_client, "mp_release_en.csv")
    s1 = (await api_auth_client.get("/api/v1/finance/summary")).json()
    assert Decimal(s1["balance"]) == Decimal(s0["balance"]) + Decimal("1485.25")

    r = await api_auth_client.delete(f"{BASE}/{p['batch_id']}")
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "undone" and out["undone_at"]
    s2 = (await api_auth_client.get("/api/v1/finance/summary")).json()
    assert Decimal(s2["balance"]) == Decimal(s0["balance"])
    lote = [t for t in await _txs(db_session, test_user.id) if t.import_batch_id]
    assert len(lote) == 3 and all(t.is_deleted and t.deleted_at for t in lote)
    # El movimiento manual sigue.
    assert any(t.product_name == "Manual" and not t.is_deleted for t in await _txs(db_session, test_user.id))

    assert (await api_auth_client.delete(f"{BASE}/{p['batch_id']}")).status_code == 409
    p2 = (await _preview(api_auth_client, "mp_release_en.csv")).json()
    assert p2["counts"]["ok"] == 3  # re-importable
    assert not any("Ya importaste" in w for w in p2["warnings"])


async def test_deshacer_informa_los_editados(api_auth_client, db_session, test_user):
    p, _ = await _import(api_auth_client, "mp_release_en.csv")
    # La comparacion es a segundo entero (SQLite no guarda fracciones): se corre
    # la confirmacion 10 s para que el update de abajo caiga despues.
    batch = await db_session.get(ImportBatch, p["batch_id"])
    batch.confirmed_at = batch.confirmed_at - timedelta(seconds=10)
    for t in await _txs(db_session, test_user.id):
        t.updated_at = t.updated_at - timedelta(seconds=10)
    await db_session.commit()
    tx = (await _txs(db_session, test_user.id))[0]
    r = await api_auth_client.put(f"/api/v1/finance/transactions/{tx.id}", json={"notes": "editado"})
    assert r.status_code == 200
    detail = (await api_auth_client.get(f"{BASE}/{p['batch_id']}")).json()
    assert detail["edited_count"] == 1
    listing = (await api_auth_client.get(BASE)).json()
    assert listing[0]["id"] == p["batch_id"] and listing[0]["edited_count"] == 1


async def test_deshacer_no_rompe_las_recurrentes(api_auth_client, db_session, test_user):
    from app.modules.recurrentes.models import RecurringOccurrence, RecurringTransaction

    rec = RecurringTransaction(
        user_id=test_user.id, type="expense", name="Alquiler", amount=Decimal("500"), currency="ARS",
        frequency="monthly", interval_count=1, day_of_month=5, start_date=date(2026, 1, 5),
        anchor_date=date(2026, 1, 5), next_occurrence_date=date(2026, 11, 5), status="active",
    )
    db_session.add(rec)
    await db_session.flush()
    manual = Transaction(
        user_id=test_user.id, amount=Decimal("500"), type="expense", currency="ARS",
        transaction_date="2026-10-05", product_name="Alquiler", account_type="cash",
        payment_method="cash", is_recurring=True, recurring_parent_id=rec.id,
    )
    db_session.add(manual)
    await db_session.flush()
    db_session.add(RecurringOccurrence(
        user_id=test_user.id, recurrence_id=rec.id, occurrence_date=date(2026, 10, 5),
        status="generated", transaction_id=manual.id,
    ))
    await db_session.commit()
    p, _ = await _import(api_auth_client, "mp_release_en.csv")
    r = await api_auth_client.delete(f"{BASE}/{p['batch_id']}")
    assert r.status_code == 200
    await db_session.refresh(manual)
    assert manual.is_deleted is False and manual.recurring_parent_id == rec.id
    occ = (await db_session.execute(select(RecurringOccurrence))).scalars().all()
    assert len(occ) == 1 and occ[0].transaction_id == manual.id


async def test_descartar_un_preview_da_204_y_lo_borra(api_auth_client, db_session):
    p = (await _preview(api_auth_client, "mp_release_en.csv")).json()
    r = await api_auth_client.delete(f"{BASE}/{p['batch_id']}")
    assert r.status_code == 204
    assert await db_session.get(ImportBatch, p["batch_id"]) is None
    assert (await api_auth_client.get(f"{BASE}/{p['batch_id']}")).status_code == 404


async def test_historial_solo_confirmados_y_deshechos(api_auth_client):
    await _preview(api_auth_client, "mp_account_money.csv")  # queda en preview
    a, _ = await _import(api_auth_client, "mp_release_en.csv")
    b, _ = await _import(api_auth_client, "banco_generico_cp1252.csv")
    await api_auth_client.delete(f"{BASE}/{b['batch_id']}")
    listing = (await api_auth_client.get(BASE)).json()
    assert [(x["id"], x["status"]) for x in listing] == [(b["batch_id"], "undone"), (a["batch_id"], "confirmed")]
    assert listing[1]["filename"] == "mp_release_en.csv" and listing[1]["imported_count"] == 3
    assert len((await api_auth_client.get(BASE, params={"limit": 1})).json()) == 1
    assert (await api_auth_client.get(BASE, params={"limit": 500})).status_code == 422


# ── Limpieza de previews ────────────────────────────────────────────────────


async def test_previews_vencidos_se_limpian_y_hay_tope_de_abiertos(api_auth_client, db_session, test_user):
    viejo = (await _preview(api_auth_client, "mp_release_en.csv")).json()
    batch = await db_session.get(ImportBatch, viejo["batch_id"])
    batch.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.commit()
    ids = []
    for i in range(6):
        ids.append((await _preview(api_auth_client, f"fecha,descripcion,monto\n2026-10-01,x{i},-1\n".encode())).json()["batch_id"])
    abiertos = (await db_session.execute(
        select(ImportBatch.id).where(ImportBatch.user_id == test_user.id, ImportBatch.status == "preview")
    )).scalars().all()
    assert viejo["batch_id"] not in abiertos
    assert len(abiertos) == 5 and ids[0] not in abiertos and ids[-1] in abiertos


async def test_rate_limit_del_preview(api_auth_client, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    last = None
    for _ in range(21):
        last = await _preview(api_auth_client, b"fecha,descripcion,monto\n2026-10-01,x,-1\n")
    assert last.status_code == 429 and "retry-after" in last.headers


# ── Seguridad del contenido ─────────────────────────────────────────────────


async def test_importa_texto_con_formulas_tal_cual_y_el_export_lo_escapa(api_auth_client, db_session, test_user):
    p, out = await _import(api_auth_client, "inyeccion_formulas.csv")
    assert out["imported_count"] == 3
    names = sorted(t.product_name for t in await _txs(db_session, test_user.id))
    assert names == ['+1+1', '=HYPERLINK("http://x","clic")', '@SUM(A1)']
    r = await api_auth_client.get(
        "/api/v1/finance/export", params={"format": "xlsx", "date_from": "2026-10-01", "date_to": "2026-10-31"}
    )
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(r.content))
    for ws in wb.worksheets:
        assert all(c.data_type != "f" for row in ws.iter_rows() for c in row)


async def test_xlsx_con_formula_sin_valor_es_error_de_fila(api_auth_client):
    wb = Workbook()
    ws = wb.active
    ws.append(["fecha", "descripcion", "monto"])
    ws.append(["2026-10-01", "ok", -10])
    ws.append(["2026-10-02", "con formula", "=1+1"])
    buf = io.BytesIO()
    wb.save(buf)
    p = (await _preview(api_auth_client, buf.getvalue(), "x.xlsx")).json()
    assert p["counts"]["ok"] == 1 and p["counts"]["error"] == 1
    assert "fórmula" in _rows(p, "error")[0]["errors"][0]


async def test_el_nombre_del_archivo_se_sanea(api_auth_client, db_session):
    r = await _preview(api_auth_client, b"fecha,descripcion,monto\n2026-10-01,x,-1\n", "..\\..\\etc/pass\x00wd<script>.csv")
    assert r.status_code == 201
    assert r.json()["filename"] == "pass wd<script>.csv".replace("\x00", " ") or "/" not in r.json()["filename"]
    assert "\\" not in r.json()["filename"] and ".." not in r.json()["filename"]


# ── Aislamiento entre usuarios ──────────────────────────────────────────────


async def test_aislamiento_de_lotes_entre_usuarios(api_auth_client, db_session, test_user):
    p, _ = await _import(api_auth_client, "mp_release_en.csv")
    q = (await _preview(api_auth_client, "banco_generico_cp1252.csv")).json()
    otro = await _otro()
    try:
        for batch_id in (p["batch_id"], q["batch_id"]):
            assert (await otro.get(f"{BASE}/{batch_id}")).status_code == 404
            assert (await otro.delete(f"{BASE}/{batch_id}")).status_code == 404
            assert (await otro.put(f"{BASE}/{batch_id}/mapping", json={"header_row": 0})).status_code == 404
            assert (await otro.post(f"{BASE}/{batch_id}/confirm", json={"rows": []})).status_code == 404
        assert (await otro.get(BASE)).json() == []
        # El lote del primero sigue intacto.
        assert (await api_auth_client.get(f"{BASE}/{p['batch_id']}")).json()["status"] == "confirmed"
    finally:
        await otro.aclose()


async def test_aislamiento_de_categorias_cuentas_y_sugerencias(api_auth_client, db_session, test_user):
    otro = await _otro()
    try:
        cat = (await otro.post("/api/v1/finance/categories", json={"name": "Supermercado"})).json()
        acc = (await otro.post("/api/v1/finance/accounts", json={
            "name": "Ajena", "account_type": "checking"})).json()
        await otro.post("/api/v1/finance/transactions", json={
            "amount": "10", "type": "expense", "transaction_date": date.today().isoformat(),
            "account_type": "cash", "payment_method": "cash", "product_name": "Compra Coto Sucursal",
            "category_id": cat["id"],
        })
        # account_id ajeno en el preview.
        r = await _preview(api_auth_client, "banco_generico_cp1252.csv", account_id=acc["id"])
        assert r.status_code == 404
        # La sugerencia no usa categorias ni historial de otro usuario.
        p = (await _preview(api_auth_client, "banco_generico_cp1252.csv")).json()
        assert all(r["suggested_category_id"] is None for r in p["rows"])
        # category_id ajena en el confirm.
        body = {"rows": [{"index": _rows(p, "ok")[0]["index"], "include": True, "category_id": cat["id"]}]}
        r = await api_auth_client.post(f"{BASE}/{p['batch_id']}/confirm", json=body)
        assert r.status_code == 404
        # Duplicados: lo que importo el otro no marca nada en mi archivo.
        await _import(otro, "banco_generico_cp1252.csv")
        p2 = (await _preview(api_auth_client, "banco_generico_cp1252.csv")).json()
        assert p2["counts"]["duplicate"] == 0 and p2["counts"]["possible_duplicate"] == 0
    finally:
        await otro.aclose()

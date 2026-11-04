"""Exportador .xlsx (openpyxl en modo write-only: memoria acotada).

Todo texto pasa por `safe_text` y se fuerza a tipo string: openpyxl interpreta
como FORMULA cualquier `str` que empiece con `=` si no se fuerza el tipo.
"""

from datetime import datetime
from decimal import Decimal
from typing import IO, Optional

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Font, PatternFill

from app.modules.finanzas.transfer import cells
from app.modules.finanzas.transfer.report_data import (
    ASSET_TYPE_LABELS,
    ReportData,
)

MONEY_FMT = "#,##0.00;[Red]-#,##0.00"
DATE_FMT = "DD/MM/YYYY"
_HEADER_FONT = Font(bold=True)
_HEADER_FILL = PatternFill("solid", fgColor="E5E7EB")
_TITLE_FONT = Font(bold=True, size=14)


def _text(ws, value: Optional[str], *, bold: bool = False, font: Optional[Font] = None):
    cell = WriteOnlyCell(ws, value=cells.safe_text(value))
    cell.data_type = "s"
    if font is not None:
        cell.font = font
    elif bold:
        cell.font = _HEADER_FONT
    return cell


def _header(ws, labels: list[str]):
    out = []
    for label in labels:
        c = _text(ws, label, bold=True)
        c.fill = _HEADER_FILL
        out.append(c)
    return out


def _money(ws, value: Optional[Decimal]):
    if value is None:
        return None
    c = WriteOnlyCell(ws, value=value)
    c.number_format = MONEY_FMT
    return c


def _date(ws, d):
    if d is None:
        return None
    c = WriteOnlyCell(ws, value=datetime(d.year, d.month, d.day))
    c.number_format = DATE_FMT
    return c


def _int(ws, n: int):
    return WriteOnlyCell(ws, value=int(n))


def _widths(ws, widths: list[float]):
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(ord("A") + i)].width = w


def _sheet(wb: Workbook, title: str, widths: list[float], freeze: Optional[str] = "A2"):
    ws = wb.create_sheet(title)
    _widths(ws, widths)
    if freeze:
        ws.freeze_panes = freeze
    return ws


def build_xlsx(data: ReportData, out: IO[bytes]) -> None:
    wb = Workbook(write_only=True)
    wb.properties.creator = "Can_cen"
    wb.properties.title = "Can_cen — Reporte de Finanzas"
    f = data.filters

    # 1. Resumen
    ws = _sheet(wb, "Resumen", [34, 18, 18, 18, 14], freeze=None)
    ws.append([_text(ws, "Can_cen — Reporte de Finanzas", font=_TITLE_FONT)])
    ws.append([_text(ws, f"Período: {cells.format_date_ar(f.date_from)} al {cells.format_date_ar(f.date_to)}")])
    ws.append(
        [_text(ws, "Filtros: " + ("; ".join(data.filter_labels) if data.filter_labels else "ninguno"))]
    )
    ws.append(
        [_text(ws, f"Generado el {data.generated_at.strftime('%d/%m/%Y %H:%M')} (hora local)")]
    )
    ws.append([])
    ws.append(_header(ws, ["Moneda", "Ingresos", "Egresos", "Balance", "Movimientos"]))
    for t in data.totals_by_currency:
        ws.append(
            [_text(ws, t.currency), _money(ws, t.income), _money(ws, t.expense),
             _money(ws, t.balance), _int(ws, t.count)]
        )
    if not data.totals_by_currency:
        ws.append([_text(ws, "Sin movimientos en el período")])

    # 2. Movimientos
    ws = _sheet(wb, "Movimientos", [12, 8, 10, 36, 24, 20, 20, 24, 8, 16, 30, 24])
    ws.auto_filter.ref = "A1:L1"
    ws.append(
        _header(
            ws,
            ["Fecha", "Hora", "Tipo", "Descripción", "Comercio", "Categoría", "Medio de pago",
             "Cuenta", "Moneda", "Monto", "Notas", "Importado"],
        )
    )
    for r in data.rows:
        ws.append(
            [
                _date(ws, r.date),
                _text(ws, r.time.strftime("%H:%M") if r.time else ""),
                _text(ws, cells.TYPE_LABELS.get(r.type, r.type)),
                _text(ws, r.description),
                _text(ws, r.merchant),
                _text(ws, r.category),
                _text(ws, cells.PAYMENT_LABELS.get(r.payment_method, r.payment_method)),
                _text(ws, r.account),
                _text(ws, r.currency),
                _money(ws, r.amount),
                _text(ws, r.notes),
                _text(ws, r.batch),
            ]
        )

    # 3. Por categoría
    ws = _sheet(wb, "Por categoría", [30, 10, 18, 18, 14])
    ws.append(_header(ws, ["Categoría", "Moneda", "Ingresos", "Egresos", "Movimientos"]))
    for c in data.by_category:
        ws.append(
            [_text(ws, c.category), _text(ws, c.currency), _money(ws, c.income),
             _money(ws, c.expense), _int(ws, c.count)]
        )

    # 4. Por mes
    ws = _sheet(wb, "Por mes", [12, 10, 18, 18, 18])
    ws.append(_header(ws, ["Mes", "Moneda", "Ingresos", "Egresos", "Balance"]))
    for m in data.by_month:
        ws.append(
            [_text(ws, m.month), _text(ws, m.currency), _money(ws, m.income),
             _money(ws, m.expense), _money(ws, m.balance)]
        )

    # 5. Inversiones (+ cotizaciones) y 6. Recurrentes
    if data.investments is not None:
        inv = data.investments
        ws = _sheet(wb, "Inversiones", [18, 34, 10, 18, 18, 18, 14], freeze=None)
        ws.append(_header(ws, ["Tipo", "Activo", "Moneda", "Invertido", "Valor actual", "Ganancia", "Vencimiento"]))
        for r in inv.rows:
            ws.append(
                [_text(ws, ASSET_TYPE_LABELS.get(r.asset_type, r.asset_type)), _text(ws, r.name),
                 _text(ws, r.currency), _money(ws, r.invested), _money(ws, r.value),
                 _money(ws, r.gain), _date(ws, r.maturity)]
            )
        ws.append([])
        ws.append([_text(ws, "Patrimonio", bold=True), _text(ws, "", bold=True),
                   _text(ws, "ARS", bold=True), _text(ws, "USD", bold=True)])
        ws.append([_text(ws, "Disponible"), None, _money(ws, inv.cash_balance_ars), _money(ws, inv.cash_balance_usd)])
        ws.append([_text(ws, "Inversiones"), None, _money(ws, inv.investments_ars), _money(ws, inv.investments_usd)])
        ws.append([_text(ws, "Total"), None, _money(ws, inv.net_worth_ars), _money(ws, inv.net_worth_usd)])
        if inv.missing_rates:
            ws.append([_text(ws, "Sin cotización: " + ", ".join(inv.missing_rates))])
        ws.append([])
        ws.append([_text(ws, "Cotizaciones", bold=True)])
        ws.append(_header(ws, ["Moneda", "Cotización", "Fuente", "Actualizada"]))
        for rt in inv.rates:
            ws.append(
                [_text(ws, rt.label), _money(ws, rt.value) if rt.value is not None else _text(ws, "Sin cotización"),
                 _text(ws, rt.source), _text(ws, rt.as_of.strftime("%d/%m/%Y %H:%M") if rt.as_of else "")]
            )

        ws = _sheet(wb, "Recurrentes", [34, 10, 16, 10, 20, 14, 12])
        ws.append(_header(ws, ["Nombre", "Tipo", "Monto", "Moneda", "Frecuencia", "Próxima", "Estado"]))
        for rr in data.recurring or []:
            ws.append(
                [_text(ws, rr.name), _text(ws, cells.TYPE_LABELS.get(rr.type, rr.type)),
                 _money(ws, rr.amount) if rr.amount is not None else _text(ws, "Variable"),
                 _text(ws, rr.currency), _text(ws, rr.frequency), _date(ws, rr.next_date),
                 _text(ws, rr.status)]
            )

    wb.save(out)

"""Exportador PDF (reportlab Platypus, A4, Helvetica).

Los textos del usuario pasan por `pdf_safe` (Helvetica es WinAnsi: los emojis
se quitan en vez de fallar) y se escapan para el mini-HTML de Paragraph.
"""

from decimal import Decimal
from typing import IO, Optional
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.modules.finanzas.transfer import cells
from app.modules.finanzas.transfer.report_data import (
    ASSET_TYPE_LABELS,
    CategoryTotals,
    ReportData,
)

INK = colors.HexColor("#1f2937")
MUTED = colors.HexColor("#6b7280")
GREEN = colors.HexColor("#047857")
RED = colors.HexColor("#b91c1c")
BRAND = colors.HexColor("#4f46e5")
HEAD_BG = colors.HexColor("#e5e7eb")
ZEBRA = colors.HexColor("#f9fafb")
MARGIN = 15 * mm
TOP_CATEGORIES = 15
DESC_MAX = 60

_styles = getSampleStyleSheet()
H2 = ParagraphStyle("h2", parent=_styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, textColor=INK, spaceBefore=10, spaceAfter=4)
CELL = ParagraphStyle("cell", parent=_styles["Normal"], fontName="Helvetica", fontSize=7.5, leading=9, textColor=INK)
NOTE = ParagraphStyle("note", parent=_styles["Normal"], fontName="Helvetica", fontSize=8, textColor=MUTED)


def _p(text: Optional[str], style=CELL) -> Paragraph:
    return Paragraph(escape(cells.pdf_safe(text)), style)


def _trunc(text: str, n: int = DESC_MAX) -> str:
    text = cells.pdf_safe(text)
    return text if len(text) <= n else text[: n - 1] + "…".encode("cp1252").decode("cp1252")


class _NumberedCanvas(rl_canvas.Canvas):
    """Canvas en dos pasadas para escribir "Página X de Y"."""

    generated_label = ""  # lo fija una subclase por request (ver build_pdf)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_pages = []

    def showPage(self):
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_pages)
        for state in self._saved_pages:
            self.__dict__.update(state)
            self._footer(total)
            super().showPage()
        super().save()

    def _footer(self, total: int):
        self.setFont("Helvetica", 8)
        self.setFillColor(MUTED)
        self.drawString(MARGIN, 9 * mm, cells.pdf_safe(self.generated_label))
        self.drawRightString(A4[0] - MARGIN, 9 * mm, f"Página {self._pageNumber} de {total}")


def _money_cell(amount: Decimal, currency: str, signed_color: bool = True) -> Paragraph:
    color = INK
    if signed_color:
        color = RED if amount < 0 else GREEN
    style = ParagraphStyle("m", parent=CELL, alignment=2, textColor=color)
    return Paragraph(escape(cells.format_money_ar(amount, currency)), style)


def _table(rows, col_widths, repeat=1, zebra=True, right_cols=()):
    t = Table(rows, colWidths=col_widths, repeatRows=repeat)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, MUTED),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    if zebra:
        for i in range(2, len(rows), 2):
            style.append(("BACKGROUND", (0, i), (-1, i), ZEBRA))
    for c in right_cols:
        style.append(("ALIGN", (c, 0), (c, 0), "RIGHT"))
    t.setStyle(TableStyle(style))
    return t


def _head(labels):
    return [Paragraph(f"<b>{escape(x)}</b>", CELL) for x in labels]


def _top_categories(items: list[CategoryTotals]) -> list[CategoryTotals]:
    """Top 15 por moneda + "Otras" (la fila "Sin categoria" va siempre al final)."""
    out: list[CategoryTotals] = []
    for currency in dict.fromkeys(c.currency for c in items):
        group = [c for c in items if c.currency == currency]
        named = [c for c in group if c.category != "Sin categoría"]
        sin = [c for c in group if c.category == "Sin categoría"]
        head, rest = named[:TOP_CATEGORIES], named[TOP_CATEGORIES:]
        out.extend(head)
        if rest:
            out.append(
                CategoryTotals(
                    "Otras", currency,
                    income=sum((c.income for c in rest), Decimal(0)),
                    expense=sum((c.expense for c in rest), Decimal(0)),
                    count=sum(c.count for c in rest),
                )
            )
        out.extend(sin)
    return out


def build_pdf(data: ReportData, out: IO[bytes]) -> None:
    f = data.filters
    period = f"{cells.format_date_ar(f.date_from)} al {cells.format_date_ar(f.date_to)}"
    label = f"Generado el {data.generated_at.strftime('%d/%m/%Y %H:%M')}"
    # Una subclase por llamada: se genera en el threadpool y un atributo de
    # clase compartido se pisaria entre dos exports simultaneos.
    canvas_cls = type("_Canvas", (_NumberedCanvas,), {"generated_label": label})

    def on_page(canvas, doc):
        canvas.saveState()
        top = A4[1] - 12 * mm
        canvas.setStrokeColor(BRAND)
        canvas.setFillColor(BRAND)
        canvas.roundRect(MARGIN, top - 7 * mm, 11 * mm, 7 * mm, 1.5 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawCentredString(MARGIN + 5.5 * mm, top - 4.8 * mm, "C_C")
        canvas.setFillColor(INK)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(MARGIN + 14 * mm, top - 3 * mm, "Can_cen")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN + 14 * mm, top - 6.5 * mm, "Reporte de Finanzas")
        canvas.drawRightString(A4[0] - MARGIN, top - 4 * mm, f"Período: {period}")
        canvas.setStrokeColor(HEAD_BG)
        canvas.line(MARGIN, top - 9 * mm, A4[0] - MARGIN, top - 9 * mm)
        canvas.restoreState()

    doc = SimpleDocTemplate(
        out, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=26 * mm, bottomMargin=16 * mm,
        title="Can_cen — Reporte de Finanzas", author="Can_cen",
    )
    width = A4[0] - 2 * MARGIN
    story = []

    # Resumen
    story.append(Paragraph("Resumen", H2))
    if data.filter_labels:
        story.append(_p("Filtros: " + "; ".join(data.filter_labels), NOTE))
        story.append(Spacer(1, 3))
    if data.totals_by_currency:
        rows = [_head(["Moneda", "Ingresos", "Egresos", "Balance", "Movimientos"])]
        for t in data.totals_by_currency:
            rows.append(
                [_p(t.currency), _money_cell(t.income, t.currency, False),
                 _money_cell(t.expense, t.currency, False),
                 _money_cell(t.balance, t.currency), _p(str(t.count))]
            )
        story.append(_table(rows, [width * x for x in (0.14, 0.24, 0.24, 0.24, 0.14)], right_cols=(1, 2, 3)))
    else:
        story.append(_p("Sin movimientos en el período.", NOTE))

    # Por mes
    if data.by_month:
        story.append(Paragraph("Por mes", H2))
        rows = [_head(["Mes", "Moneda", "Ingresos", "Egresos", "Balance"])]
        for m in data.by_month:
            rows.append(
                [_p(m.month), _p(m.currency), _money_cell(m.income, m.currency, False),
                 _money_cell(m.expense, m.currency, False), _money_cell(m.balance, m.currency)]
            )
        story.append(_table(rows, [width * x for x in (0.14, 0.12, 0.25, 0.25, 0.24)], right_cols=(2, 3, 4)))

    # Por categoria
    if data.by_category:
        story.append(Paragraph("Por categoría", H2))
        rows = [_head(["Categoría", "Moneda", "Ingresos", "Egresos", "Mov."])]
        for c in _top_categories(data.by_category):
            rows.append(
                [_p(c.category), _p(c.currency), _money_cell(c.income, c.currency, False),
                 _money_cell(c.expense, c.currency, False), _p(str(c.count))]
            )
        story.append(_table(rows, [width * x for x in (0.34, 0.1, 0.24, 0.24, 0.08)], right_cols=(2, 3)))

    # Movimientos
    story.append(Paragraph("Movimientos", H2))
    if data.rows:
        rows = [_head(["Fecha", "Descripción", "Categoría", "Medio", "Mon.", "Monto"])]
        for r in data.rows:
            rows.append(
                [_p(cells.format_date_ar(r.date)), _p(_trunc(r.description)),
                 _p(_trunc(r.category, 24)),
                 _p(cells.PAYMENT_LABELS.get(r.payment_method, r.payment_method)),
                 _p(r.currency), _money_cell(r.amount, r.currency)]
            )
        story.append(_table(rows, [width * x for x in (0.11, 0.35, 0.18, 0.14, 0.06, 0.16)], right_cols=(5,)))
    else:
        story.append(_p("Sin movimientos en el período.", NOTE))

    # Inversiones y patrimonio
    inv = data.investments
    if inv is not None:
        story.append(Paragraph("Inversiones y patrimonio", H2))
        if inv.rows:
            rows = [_head(["Tipo", "Activo", "Mon.", "Invertido", "Valor actual", "Ganancia"])]
            for r in inv.rows:
                rows.append(
                    [_p(ASSET_TYPE_LABELS.get(r.asset_type, r.asset_type)), _p(_trunc(r.name, 40)),
                     _p(r.currency), _money_cell(r.invested, r.currency, False),
                     _money_cell(r.value, r.currency, False), _money_cell(r.gain, r.currency)]
                )
            story.append(_table(rows, [width * x for x in (0.14, 0.30, 0.07, 0.17, 0.17, 0.15)], right_cols=(3, 4, 5)))
        else:
            story.append(_p("Sin inversiones activas.", NOTE))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Patrimonio", H2))

        def amt(v, cur):
            return _money_cell(v, cur, False) if v is not None else _p("Sin cotización")

        rows = [
            _head(["", "ARS", "USD"]),
            [_p("Disponible"), amt(inv.cash_balance_ars, "ARS"), amt(inv.cash_balance_usd, "USD")],
            [_p("Inversiones"), amt(inv.investments_ars, "ARS"), amt(inv.investments_usd, "USD")],
            [_p("Total"), amt(inv.net_worth_ars, "ARS"), amt(inv.net_worth_usd, "USD")],
        ]
        story.append(_table(rows, [width * x for x in (0.3, 0.35, 0.35)], right_cols=(1, 2)))
        story.append(Spacer(1, 6))
        rows = [_head(["Cotización", "Valor", "Fuente", "Actualizada"])]
        for rt in inv.rates:
            rows.append(
                [_p(rt.label), amt(rt.value, "ARS"), _p(rt.source),
                 _p(rt.as_of.strftime("%d/%m/%Y %H:%M") if rt.as_of else "")]
            )
        story.append(_table(rows, [width * x for x in (0.3, 0.25, 0.2, 0.25)], right_cols=(1,)))

    # Recurrentes
    if data.recurring:
        story.append(Paragraph("Movimientos recurrentes", H2))
        rows = [_head(["Nombre", "Tipo", "Monto", "Frecuencia", "Próxima", "Estado"])]
        for r in data.recurring:
            rows.append(
                [_p(_trunc(r.name, 40)), _p(cells.TYPE_LABELS.get(r.type, r.type)),
                 _money_cell(r.amount, r.currency, False) if r.amount is not None else _p("Variable"),
                 _p(r.frequency), _p(cells.format_date_ar(r.next_date) if r.next_date else "—".encode("cp1252").decode("cp1252")),
                 _p(r.status)]
            )
        story.append(_table(rows, [width * x for x in (0.30, 0.1, 0.2, 0.16, 0.14, 0.1)], right_cols=(2,)))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page, canvasmaker=canvas_cls)

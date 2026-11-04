"""Datos del reporte de Finanzas, compartidos por el exportador Excel y el PDF.

Una sola consulta de movimientos (usuario, no borrados, filtros) y todos los
agregados se calculan en Python sobre esas mismas filas: los totales siempre
cuadran con el detalle. Nunca se suman monedas distintas.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.clock import local_today
from app.modules.finanzas.models import BankAccount, Category, Transaction
from app.modules.finanzas.transfer.models import ImportBatch
from app.modules.inversiones.service import InvestmentService
from app.modules.inversiones.valuation import valuate
from app.modules.recurrentes.models import RecurringTransaction

ZERO = Decimal("0")
MAX_RANGE_DAYS = 366 * 5 + 1
NO_CATEGORY = "Sin categoría"
FORMAT_LABEL = {"xlsx": "Excel", "pdf": "PDF"}

ASSET_TYPE_LABELS = {
    "stock": "Acciones",
    "fixed_term": "Plazo fijo",
    "crypto": "Cripto",
    "bond": "Bonos",
    "fund": "Fondos",
    "fx": "Divisas",
    "real_estate": "Inmueble",
    "vehicle": "Vehículo",
    "other": "Otro",
}
FREQUENCY_LABELS = {"daily": "Diaria", "weekly": "Semanal", "monthly": "Mensual", "yearly": "Anual"}
STATUS_LABELS = {"active": "Activa", "paused": "Pausada"}


def to_decimal(value) -> Decimal:
    """SQLite devuelve `float` para Numeric y Postgres `Decimal`."""
    if value is None:
        return ZERO
    return value if isinstance(value, Decimal) else Decimal(str(value))


@dataclass
class ReportFilters:
    date_from: date
    date_to: date
    type: Optional[str] = None
    category_id: Optional[str] = None  # id propio o "none"
    account_id: Optional[str] = None
    include_investments: bool = False

    @classmethod
    def resolve(
        cls,
        date_from: Optional[date],
        date_to: Optional[date],
        tz_offset_minutes: int,
        **kw,
    ) -> "ReportFilters":
        today = local_today(tz_offset_minutes)
        d_to = date_to or today
        d_from = date_from or (d_to.replace(day=1) if date_to else today.replace(day=1))
        if d_to < d_from:
            raise HTTPException(
                status_code=422, detail="La fecha 'hasta' no puede ser anterior a la fecha 'desde'."
            )
        if (d_to - d_from).days > MAX_RANGE_DAYS:
            raise HTTPException(status_code=422, detail="El rango máximo es de 5 años.")
        return cls(date_from=d_from, date_to=d_to, **kw)


@dataclass
class ReportRow:
    date: date
    time: Optional[time]
    type: str
    description: str
    merchant: str
    category: str
    payment_method: str
    account: str
    currency: str
    amount: Decimal  # con signo: egreso negativo
    notes: str
    batch: str


@dataclass
class CurrencyTotals:
    currency: str
    income: Decimal = ZERO
    expense: Decimal = ZERO
    count: int = 0

    @property
    def balance(self) -> Decimal:
        return self.income - self.expense


@dataclass
class CategoryTotals:
    category: str
    currency: str
    income: Decimal = ZERO
    expense: Decimal = ZERO
    count: int = 0


@dataclass
class MonthTotals:
    month: str
    currency: str
    income: Decimal = ZERO
    expense: Decimal = ZERO

    @property
    def balance(self) -> Decimal:
        return self.income - self.expense


@dataclass
class InvestmentRow:
    asset_type: str
    name: str
    currency: str
    invested: Decimal
    value: Decimal
    gain: Decimal
    maturity: Optional[date]


@dataclass
class RateRow:
    label: str
    value: Optional[Decimal]
    source: str
    as_of: Optional[datetime]


@dataclass
class InvestmentBlock:
    rows: list[InvestmentRow]
    cash_balance_ars: Decimal
    investments_ars: Optional[Decimal]
    net_worth_ars: Optional[Decimal]
    net_worth_usd: Optional[Decimal]
    cash_balance_usd: Optional[Decimal]
    investments_usd: Optional[Decimal]
    rates: list[RateRow]
    missing_rates: list[str]


@dataclass
class RecurringRow:
    name: str
    type: str
    amount: Optional[Decimal]
    currency: str
    frequency: str
    next_date: Optional[date]
    status: str


@dataclass
class ReportData:
    filters: ReportFilters
    generated_at: datetime  # hora local del usuario
    rows: list[ReportRow] = field(default_factory=list)
    totals_by_currency: list[CurrencyTotals] = field(default_factory=list)
    by_category: list[CategoryTotals] = field(default_factory=list)
    by_month: list[MonthTotals] = field(default_factory=list)
    investments: Optional[InvestmentBlock] = None
    recurring: Optional[list[RecurringRow]] = None
    filter_labels: list[str] = field(default_factory=list)


def _conditions(user_id: str, f: ReportFilters, account: Optional[BankAccount]):
    conds = [
        Transaction.user_id == user_id,
        Transaction.is_deleted == False,  # noqa: E712
        Transaction.transaction_date >= f.date_from,
        Transaction.transaction_date <= f.date_to,
    ]
    if f.type:
        conds.append(Transaction.type == f.type)
    if f.category_id == "none":
        conds.append(Transaction.category_id.is_(None))
    elif f.category_id:
        conds.append(Transaction.category_id == f.category_id)
    if account is not None:
        conds.append(Transaction.account_type == account.account_type)
        conds.append(Transaction.account_last4 == (account.last4 or ""))
        if account.bank_name:
            conds.append(Transaction.bank_entity_name == account.bank_name)
    return and_(*conds)


async def _resolve_scope(db: AsyncSession, user_id: str, f: ReportFilters):
    """404 si la categoria o la cuenta no son del usuario."""
    category = None
    if f.category_id and f.category_id != "none":
        category = (
            await db.execute(
                select(Category).where(Category.id == f.category_id, Category.user_id == user_id)
            )
        ).scalar_one_or_none()
        if category is None:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
    account = None
    if f.account_id:
        account = (
            await db.execute(
                select(BankAccount).where(
                    BankAccount.id == f.account_id, BankAccount.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        if account is None:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return category, account


async def check_row_limit(
    db: AsyncSession, user_id: str, f: ReportFilters, fmt: str
) -> tuple[Optional[Category], Optional[BankAccount]]:
    """Valida el alcance y cuenta primero: si se pasa del tope responde 422
    sin generar nada."""
    category, account = await _resolve_scope(db, user_id, f)
    total = (
        await db.execute(
            select(func.count()).select_from(Transaction).where(_conditions(user_id, f, account))
        )
    ).scalar_one()
    limit = (
        settings.FINANCE_EXPORT_MAX_ROWS_XLSX if fmt == "xlsx" else settings.FINANCE_EXPORT_MAX_ROWS_PDF
    )
    if total > limit:
        raise HTTPException(
            status_code=422,
            detail=(
                f"El reporte tiene {total} movimientos; el máximo para {FORMAT_LABEL[fmt]} es "
                f"{limit}. Achicá el rango de fechas."
            ),
        )
    return category, account


async def build_report(
    db: AsyncSession,
    user_id: str,
    f: ReportFilters,
    tz_offset_minutes: int,
    category: Optional[Category],
    account: Optional[BankAccount],
) -> ReportData:
    user_id = str(user_id)
    now_local = datetime.now(timezone.utc) + timedelta(minutes=tz_offset_minutes)
    data = ReportData(filters=f, generated_at=now_local.replace(tzinfo=None))

    result = await db.execute(
        select(Transaction, Category.name, ImportBatch.filename)
        .outerjoin(Category, Category.id == Transaction.category_id)
        .outerjoin(ImportBatch, ImportBatch.id == Transaction.import_batch_id)
        .where(_conditions(user_id, f, account))
        .order_by(
            Transaction.transaction_date, Transaction.transaction_time, Transaction.created_at
        )
    )
    totals: dict[str, CurrencyTotals] = {}
    cats: dict[tuple[str, str], CategoryTotals] = {}
    months: dict[tuple[str, str], MonthTotals] = {}
    for tx, cat_name, batch_name in result.all():
        amount = to_decimal(tx.amount)
        day = _as_date(tx.transaction_date)
        income = tx.type == "income"
        account_label = " ".join(
            x for x in (tx.bank_entity_name, f"·{tx.account_last4}" if tx.account_last4 else "") if x
        )
        data.rows.append(
            ReportRow(
                date=day,
                time=_as_time(tx.transaction_time),
                type=tx.type,
                description=tx.product_name or "",
                merchant=tx.merchant_name or "",
                category=cat_name or "",
                payment_method=tx.payment_method or "",
                account=account_label,
                currency=tx.currency or "ARS",
                amount=amount if income else -amount,
                notes=tx.notes or "",
                batch=batch_name or "",
            )
        )
        cur = totals.setdefault(tx.currency, CurrencyTotals(tx.currency))
        cat = cats.setdefault(
            (cat_name or NO_CATEGORY, tx.currency), CategoryTotals(cat_name or NO_CATEGORY, tx.currency)
        )
        mon = months.setdefault(
            (day.strftime("%Y-%m"), tx.currency), MonthTotals(day.strftime("%Y-%m"), tx.currency)
        )
        for acc in (cur, cat):
            acc.count += 1
        if income:
            cur.income += amount
            cat.income += amount
            mon.income += amount
        else:
            cur.expense += amount
            cat.expense += amount
            mon.expense += amount

    data.totals_by_currency = sorted(totals.values(), key=lambda t: _currency_key(t.currency))
    data.by_category = sorted(
        cats.values(),
        key=lambda c: (_currency_key(c.currency), c.category == NO_CATEGORY, -c.expense, c.category),
    )
    data.by_month = sorted(months.values(), key=lambda m: (m.month, _currency_key(m.currency)))

    data.filter_labels = _filter_labels(f, category, account)

    if f.include_investments:
        data.investments = await _investments_block(db, user_id, tz_offset_minutes)
        data.recurring = await _recurring_rows(db, user_id)
    return data


def _currency_key(currency: str) -> tuple[int, str]:
    order = {"ARS": 0, "USD": 1, "EUR": 2}
    return (order.get(currency, 9), currency)


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _as_time(value) -> Optional[time]:
    if not value:
        return None
    if isinstance(value, time):
        return value
    try:
        return time.fromisoformat(str(value))
    except ValueError:
        return None


def _filter_labels(f: ReportFilters, category, account) -> list[str]:
    labels = []
    if f.type:
        labels.append("Tipo: " + ("Ingresos" if f.type == "income" else "Egresos"))
    if f.category_id == "none":
        labels.append("Categoría: sin categoría")
    elif category is not None:
        labels.append(f"Categoría: {category.name}")
    if account is not None:
        labels.append(f"Cuenta: {account.name}")
    if f.include_investments:
        labels.append("Incluye inversiones y patrimonio")
    return labels


async def _investments_block(
    db: AsyncSession, user_id: str, tz_offset_minutes: int
) -> InvestmentBlock:
    today = local_today(tz_offset_minutes)
    svc = InvestmentService(db)
    nw = await svc.net_worth(user_id, today)
    rows = []
    for inv in await svc.repo.list(user_id, "active"):
        val = valuate(inv, today)
        rows.append(
            InvestmentRow(
                asset_type=inv.asset_type,
                name=inv.name,
                currency=inv.currency,
                invested=val.invested_amount,
                value=val.effective_value,
                gain=val.gain,
                maturity=inv.maturity_date,
            )
        )
    r = nw.rates
    rates = [
        RateRow("Dólar (USD → ARS)", r.usd_ars, r.usd_effective_source or r.usd_source, r.usd_as_of),
        RateRow("Euro (EUR → ARS)", r.eur_ars, r.eur_effective_source or r.eur_source, r.eur_as_of),
    ]
    return InvestmentBlock(
        rows=rows,
        cash_balance_ars=nw.cash_balance_ars,
        cash_balance_usd=nw.cash_balance_usd,
        investments_ars=nw.investments.total_ars,
        investments_usd=nw.investments.total_usd,
        net_worth_ars=nw.net_worth_ars,
        net_worth_usd=nw.net_worth_usd,
        rates=rates,
        missing_rates=list(nw.missing_rates),
    )


async def _recurring_rows(db: AsyncSession, user_id: str) -> list[RecurringRow]:
    result = await db.execute(
        select(RecurringTransaction)
        .where(RecurringTransaction.user_id == user_id)
        .order_by(RecurringTransaction.status, RecurringTransaction.name)
    )
    return [
        RecurringRow(
            name=r.name,
            type=r.type,
            amount=to_decimal(r.amount) if r.amount is not None else None,
            currency=r.currency,
            frequency=_frequency_label(r.frequency, r.interval_count),
            next_date=r.next_occurrence_date,
            status=STATUS_LABELS.get(r.status, r.status),
        )
        for r in result.scalars().all()
    ]


def _frequency_label(frequency: str, interval: int) -> str:
    base = FREQUENCY_LABELS.get(frequency, frequency)
    return base if not interval or interval == 1 else f"{base} (cada {interval})"

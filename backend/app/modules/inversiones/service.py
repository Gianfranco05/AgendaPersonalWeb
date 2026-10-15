from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ajustes.models import UserPreference
from app.modules.finanzas.repository import TransactionRepository
from app.modules.inversiones.models import Investment
from app.modules.inversiones.repository import InvestmentRepository
from app.modules.inversiones.schemas import (
    CurrencyBreakdown,
    FixedTermOut,
    InvestmentCreate,
    InvestmentOut,
    InvestmentSummary,
    InvestmentUpdate,
    NetWorthOut,
    RatesOut,
    TypeBreakdown,
    UpcomingMaturity,
    validate_fixed_term_state,
)
from app.modules.inversiones.valuation import (
    ZERO,
    Rates,
    Valuation,
    compute_totals,
    convert_to_ars,
    round2,
    to_decimal,
    valuate,
)

UPCOMING_DAYS = 30
UPCOMING_LIMIT = 5
CURRENCY_ORDER = ("ARS", "USD", "USDT", "EUR")

# Campos que un PUT con `null` no puede borrar: el `null` se ignora.
_REQUIRED_FIELDS = {
    "asset_type",
    "name",
    "currency",
    "invested_amount",
    "notify_maturity",
    "price_source",
    "status",
}


def _enum_values(data: dict) -> dict:
    return {k: (v.value if hasattr(v, "value") else v) for k, v in data.items()}


def _quantize_money(data: dict) -> dict:
    for key in ("invested_amount", "current_value"):
        if data.get(key) is not None:
            data[key] = round2(data[key])
    return data


def to_out(inv: Investment, today: date) -> InvestmentOut:
    val = valuate(inv, today)
    ft = val.fixed_term
    return InvestmentOut(
        id=inv.id,
        asset_type=inv.asset_type,
        name=inv.name,
        ticker=inv.ticker,
        currency=inv.currency,
        quantity=to_decimal(inv.quantity),
        invested_amount=val.invested_amount,
        current_value=round2(to_decimal(inv.current_value)) if inv.current_value is not None else None,
        interest_rate_tna=to_decimal(inv.interest_rate_tna),
        start_date=inv.start_date,
        maturity_date=inv.maturity_date,
        institution=inv.institution,
        notes=inv.notes,
        status=inv.status,
        notify_maturity=inv.notify_maturity,
        timezone_offset_minutes=inv.timezone_offset_minutes,
        price_source=inv.price_source,
        last_price=to_decimal(inv.last_price),
        last_price_at=inv.last_price_at,
        value_updated_at=inv.value_updated_at,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        effective_value=val.effective_value,
        value_source=val.value_source,
        gain=val.gain,
        gain_pct=val.gain_pct,
        days_to_maturity=val.days_to_maturity,
        is_matured=val.is_matured,
        fixed_term=FixedTermOut(
            term_days=ft.term_days,
            interest_total=ft.interest_total,
            amount_at_maturity=ft.amount_at_maturity,
            accrued_interest=ft.accrued_interest,
            tea_pct=ft.tea_pct,
        )
        if ft
        else None,
    )


class InvestmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InvestmentRepository(db)

    # ── CRUD ────────────────────────────────────────────────────────────────

    async def get(self, investment_id: str, user_id: str) -> Optional[Investment]:
        return await self.repo.get(investment_id, user_id)

    async def list(
        self, user_id: str, status_filter: str = "active", asset_type: Optional[str] = None
    ):
        return await self.repo.list(user_id, status_filter, asset_type)

    async def create(self, user_id: str, data: InvestmentCreate) -> Investment:
        values = _quantize_money(_enum_values(data.model_dump()))
        investment = Investment(user_id=user_id, status="active", **values)
        if investment.current_value is not None:
            investment.value_updated_at = datetime.now(timezone.utc)
        return await self.repo.create(investment)

    async def update(self, investment: Investment, data: InvestmentUpdate) -> Investment:
        changes = _quantize_money(_enum_values(data.model_dump(exclude_unset=True)))
        for key in _REQUIRED_FIELDS:
            if key in changes and changes[key] is None:
                del changes[key]

        # Las reglas cruzadas se validan sobre el estado resultante, no sobre
        # el payload: cambiar solo el vencimiento tiene que mirar el inicio.
        merged = SimpleNamespace(
            asset_type=investment.asset_type,
            currency=investment.currency,
            interest_rate_tna=investment.interest_rate_tna,
            start_date=investment.start_date,
            maturity_date=investment.maturity_date,
        )
        for key, value in changes.items():
            if hasattr(merged, key):
                setattr(merged, key, value)
        try:
            validate_fixed_term_state(
                merged.asset_type,
                merged.currency,
                merged.interest_rate_tna,
                merged.start_date,
                merged.maturity_date,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

        if "current_value" in changes:
            before = to_decimal(investment.current_value)
            after = changes["current_value"]
            if before != after:
                changes["value_updated_at"] = (
                    datetime.now(timezone.utc) if after is not None else None
                )
        return await self.repo.update(investment, changes)

    async def delete(self, investment: Investment) -> None:
        await self.repo.delete(investment)

    # ── Cotizaciones y preferencias ─────────────────────────────────────────

    async def _preferences(self, user_id: str) -> Optional[UserPreference]:
        result = await self.db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_rates(self, user_id: str) -> tuple[Rates, Optional[datetime], bool]:
        """(cotizaciones, ultima actualizacion, sumar inversiones al balance)."""
        prefs = await self._preferences(user_id)
        if prefs is None:
            return Rates(), None, False
        return (
            Rates(usd_ars=to_decimal(prefs.fx_usd_ars), eur_ars=to_decimal(prefs.fx_eur_ars)),
            prefs.fx_rates_updated_at,
            bool(prefs.include_investments_in_balance),
        )

    # ── Resumen y patrimonio ────────────────────────────────────────────────

    async def summary(self, user_id: str, today: date, rates: Optional[Rates] = None) -> InvestmentSummary:
        if rates is None:
            rates, _, _ = await self.get_rates(user_id)
        active = await self.repo.list(user_id, "active")
        rows = [(inv, valuate(inv, today)) for inv in active]
        return build_summary(rows, rates)

    async def net_worth(self, user_id: str, today: date) -> NetWorthOut:
        rates, rates_updated_at, include = await self.get_rates(user_id)
        summary = await self.summary(user_id, today, rates)
        balance = await TransactionRepository(self.db).get_balance(user_id)
        cash_ars = round2(to_decimal(balance["balance"]))
        cash_usd = round2(cash_ars / rates.usd_ars) if rates.usd_ars else None

        net_ars = round2(cash_ars + summary.total_ars) if summary.total_ars is not None else None
        net_usd = (
            round2(cash_usd + summary.total_usd)
            if cash_usd is not None and summary.total_usd is not None
            else None
        )
        missing = list(summary.missing_rates)
        if rates.usd_ars is None and "USD" not in missing:
            missing.insert(0, "USD")
        return NetWorthOut(
            cash_balance_ars=cash_ars,
            cash_balance_usd=cash_usd,
            investments=summary,
            net_worth_ars=net_ars,
            net_worth_usd=net_usd,
            rates=RatesOut(
                usd_ars=rates.usd_ars, eur_ars=rates.eur_ars, updated_at=rates_updated_at
            ),
            missing_rates=missing,
            include_investments_in_balance=include,
        )


def build_summary(rows: list[tuple[Investment, Valuation]], rates: Rates) -> InvestmentSummary:
    """Resumen de los activos activos (`rows` = activo + su valuacion)."""
    per_currency: dict[str, dict] = {}
    per_type: dict[str, dict] = {}
    for inv, val in rows:
        cur = per_currency.setdefault(
            inv.currency, {"invested": ZERO, "value": ZERO, "count": 0}
        )
        cur["invested"] += val.invested_amount
        cur["value"] += val.effective_value
        cur["count"] += 1

        typ = per_type.setdefault(inv.asset_type, {"count": 0, "ars": ZERO, "ok": True})
        typ["count"] += 1
        converted = convert_to_ars(val.effective_value, inv.currency, rates)
        if converted is None:
            typ["ok"] = False
        else:
            typ["ars"] += converted

    totals = compute_totals({c: d["value"] for c, d in per_currency.items()}, rates)

    by_currency = [
        CurrencyBreakdown(
            currency=c,
            invested=per_currency[c]["invested"],
            current_value=per_currency[c]["value"],
            gain=per_currency[c]["value"] - per_currency[c]["invested"],
            count=per_currency[c]["count"],
        )
        for c in CURRENCY_ORDER
        if c in per_currency
    ]
    by_type = [
        TypeBreakdown(
            asset_type=t,
            count=d["count"],
            value_ars=round2(d["ars"]) if d["ok"] else None,
        )
        for t, d in sorted(per_type.items())
    ]

    upcoming = sorted(
        (
            (inv, val)
            for inv, val in rows
            if val.days_to_maturity is not None and 0 <= val.days_to_maturity <= UPCOMING_DAYS
        ),
        key=lambda pair: (pair[1].days_to_maturity, pair[0].name),
    )[:UPCOMING_LIMIT]

    return InvestmentSummary(
        by_currency=by_currency,
        by_type=by_type,
        total_ars=totals.total_ars,
        total_usd=totals.total_usd,
        missing_rates=totals.missing_rates,
        count_active=len(rows),
        upcoming_maturities=[
            UpcomingMaturity(
                id=inv.id,
                name=inv.name,
                asset_type=inv.asset_type,
                currency=inv.currency,
                maturity_date=inv.maturity_date,
                days_to_maturity=val.days_to_maturity,
                amount=val.fixed_term.amount_at_maturity if val.fixed_term else val.effective_value,
            )
            for inv, val in upcoming
        ],
    )

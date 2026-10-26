from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Mapping, Optional

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
    PortfolioRealReturnOut,
    ProjectionOut,
    RatesOut,
    RealReturnOut,
    TypeBreakdown,
    UpcomingMaturity,
    validate_fixed_term_state,
    validate_price_source_state,
)
from app.modules.inversiones.valuation import (
    FIXED_TERM,
    PRICE_PROVIDERS,
    ZERO,
    Rates,
    Valuation,
    compute_totals,
    convert_to_ars,
    round2,
    to_decimal,
    valuate,
)
from app.modules.mercado import inflation as infl
from app.modules.mercado.providers.coingecko import vs_currency_for
from app.modules.mercado.rates import RateInfo, resolve_rate
from app.modules.mercado.repository import MarketRepository, as_utc
from app.modules.mercado.service import ensure_state_rows

#: `last_price_at` con mas de esto = cotizacion automatica desactualizada.
QUOTE_STALE_SECONDS = 3600
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


@dataclass(frozen=True)
class ResolvedRates(Rates):
    """`Rates` (lo que usan los calculos) mas de donde salio cada cotizacion."""

    usd: RateInfo = field(default_factory=lambda: RateInfo(source="mep"))
    eur: RateInfo = field(default_factory=lambda: RateInfo(source="oficial"))


def real_return_for(
    inv: Investment, val: Valuation, today: date, series: Mapping[date, Decimal]
) -> tuple[Optional[infl.RealReturn], Optional[str]]:
    """Rendimiento real de un activo, o el motivo por el que no hay."""
    if inv.currency != "ARS":
        return None, infl.REASON_CURRENCY
    if inv.start_date is None:
        return None, infl.REASON_NO_START_DATE
    end = today
    if inv.status == "closed":
        if inv.maturity_date is not None and inv.maturity_date <= today:
            end = inv.maturity_date
        elif inv.updated_at is not None:
            end = as_utc(inv.updated_at).date()
    elif inv.asset_type == FIXED_TERM and inv.maturity_date is not None and inv.maturity_date < today:
        # El devengado del plazo fijo se frena en el vencimiento.
        end = inv.maturity_date
    result, reason = infl.compute_real_return(
        invested=val.invested_amount,
        value=val.effective_value,
        start=inv.start_date,
        end=end,
        series=series,
    )
    if result is not None and inv.status == "active" and val.fixed_term is not None:
        if inv.maturity_date is not None and inv.maturity_date >= today:
            projection = infl.project_fixed_term(
                invested=val.invested_amount,
                interest_total=val.fixed_term.interest_total,
                start=inv.start_date,
                maturity=inv.maturity_date,
                series=series,
            )
            if projection is not None:
                result = _with_projection(result, projection)
    return result, reason


def _with_projection(result: infl.RealReturn, projection: infl.Projection) -> infl.RealReturn:
    return replace(result, projected_at_maturity=projection)


def _real_return_out(rr: infl.RealReturn) -> RealReturnOut:
    projection = rr.projected_at_maturity
    return RealReturnOut(
        nominal_pct=rr.nominal_pct,
        inflation_pct=rr.inflation_pct,
        real_pct=rr.real_pct,
        estimated=rr.estimated,
        estimated_months=list(rr.estimated_months),
        period_start=rr.period_start,
        period_end=rr.period_end,
        projected_at_maturity=ProjectionOut(
            nominal_pct=projection.nominal_pct,
            inflation_pct=projection.inflation_pct,
            real_pct=projection.real_pct,
            estimated=projection.estimated,
        )
        if projection
        else None,
    )


def _quote_info(inv: Investment, now: datetime) -> tuple[Optional[str], Optional[bool]]:
    if inv.price_source == "manual":
        return None, None
    provider = PRICE_PROVIDERS.get(inv.price_source)
    name = {"coingecko": "CoinGecko"}.get(inv.price_source, inv.price_source) if provider else None
    if inv.last_price_at is None:
        return name, None
    return name, (now - as_utc(inv.last_price_at)).total_seconds() > QUOTE_STALE_SECONDS


def to_out(
    inv: Investment, today: date, series: Optional[Mapping[date, Decimal]] = None
) -> InvestmentOut:
    val = valuate(inv, today)
    ft = val.fixed_term
    rr, reason = real_return_for(inv, val, today, series or {})
    quote_provider, quote_stale = _quote_info(inv, datetime.now(timezone.utc))
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
        quote_provider=quote_provider,
        quote_stale=quote_stale,
        real_return=_real_return_out(rr) if rr else None,
        real_return_unavailable_reason=None if rr else reason,
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
        primed = await self._prime_quote(investment)
        created = await self.repo.create(investment)
        if not primed:
            await self._schedule_quote_refresh(created)
        return created

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
            ticker=investment.ticker,
            quantity=investment.quantity,
            price_source=investment.price_source,
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
            validate_price_source_state(
                merged.price_source,
                merged.asset_type,
                merged.ticker,
                to_decimal(merged.quantity),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

        auto_changed = merged.price_source != "manual" and (
            merged.price_source != investment.price_source
            or merged.ticker != investment.ticker
            or merged.currency != investment.currency
        )
        if auto_changed:
            # Otro ticker/moneda = otro precio: el anterior ya no sirve.
            investment.last_price = None
            investment.last_price_at = None

        if "current_value" in changes:
            before = to_decimal(investment.current_value)
            after = changes["current_value"]
            if before != after:
                changes["value_updated_at"] = (
                    datetime.now(timezone.utc) if after is not None else None
                )
        updated = await self.repo.update(investment, changes)
        if auto_changed:
            if await self._prime_quote(updated):
                updated = await self.repo.update(updated, {})
            else:
                await self._schedule_quote_refresh(updated)
        return updated

    async def _prime_quote(self, investment: Investment) -> bool:
        """Con proveedor automatico, completa `last_price` desde el cache de
        `market_prices` (sin HTTP en el request). False si no hay precio."""
        if investment.price_source == "manual" or not investment.ticker:
            return True
        price = await MarketRepository(self.db).get_price(
            investment.price_source, investment.ticker, vs_currency_for(investment.currency)
        )
        if price is None:
            return False
        investment.last_price = to_decimal(price.price)
        investment.last_price_at = as_utc(price.source_updated_at or price.fetched_at)
        return True

    async def _schedule_quote_refresh(self, investment: Investment) -> None:
        """Sin precio en cache: el proximo ciclo del scheduler (<= 60 s) lo trae."""
        if investment.price_source == "manual":
            return
        await ensure_state_rows(self.db)
        await MarketRepository(self.db).schedule_now("crypto", datetime.now(timezone.utc))

    async def delete(self, investment: Investment) -> None:
        await self.repo.delete(investment)

    # ── Cotizaciones y preferencias ─────────────────────────────────────────

    async def _preferences(self, user_id: str) -> Optional[UserPreference]:
        result = await self.db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_rates(self, user_id: str) -> tuple[ResolvedRates, bool]:
        """(cotizaciones efectivas, sumar inversiones al balance)."""
        prefs = await self._preferences(user_id)
        snapshot = await MarketRepository(self.db).fx_snapshot()
        usd_source = prefs.fx_usd_source if prefs else "mep"
        eur_source = prefs.fx_eur_source if prefs else "oficial"
        manual_usd = to_decimal(prefs.fx_usd_ars) if prefs else None
        manual_eur = to_decimal(prefs.fx_eur_ars) if prefs else None
        manual_at = prefs.fx_rates_updated_at if prefs else None
        usd = resolve_rate("USD", usd_source, manual_usd, manual_at, snapshot)
        eur = resolve_rate("EUR", eur_source, manual_eur, manual_at, snapshot)
        rates = ResolvedRates(usd_ars=usd.rate, eur_ars=eur.rate, usd=usd, eur=eur)
        return rates, (bool(prefs.include_investments_in_balance) if prefs else False)

    # ── Resumen y patrimonio ────────────────────────────────────────────────

    async def inflation_series(self) -> Mapping[date, Decimal]:
        return await MarketRepository(self.db).inflation_series()

    async def summary(self, user_id: str, today: date, rates: Optional[Rates] = None) -> InvestmentSummary:
        if rates is None:
            rates, _ = await self.get_rates(user_id)
        active = await self.repo.list(user_id, "active")
        rows = [(inv, valuate(inv, today)) for inv in active]
        return build_summary(rows, rates, today, await self.inflation_series())

    async def net_worth(self, user_id: str, today: date) -> NetWorthOut:
        rates, include = await self.get_rates(user_id)
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
            rates=rates_out(rates),
            missing_rates=missing,
            include_investments_in_balance=include,
        )


def rates_out(rates: ResolvedRates) -> RatesOut:
    return RatesOut(
        usd_ars=rates.usd_ars,
        eur_ars=rates.eur_ars,
        updated_at=rates.usd.as_of,
        usd_source=rates.usd.source,
        usd_effective_source=rates.usd.effective_source,
        usd_buy=rates.usd.buy,
        usd_provider=rates.usd.provider,
        usd_as_of=rates.usd.as_of,
        usd_stale=rates.usd.stale,
        eur_source=rates.eur.source,
        eur_effective_source=rates.eur.effective_source,
        eur_buy=rates.eur.buy,
        eur_provider=rates.eur.provider,
        eur_as_of=rates.eur.as_of,
        eur_stale=rates.eur.stale,
    )


def build_summary(
    rows: list[tuple[Investment, Valuation]],
    rates: Rates,
    today: Optional[date] = None,
    series: Optional[Mapping[date, Decimal]] = None,
) -> InvestmentSummary:
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

    real_results: list[Optional[infl.RealReturn]] = []
    if today is not None:
        for inv, val in rows:
            if inv.currency == "ARS":
                real_results.append(real_return_for(inv, val, today, series or {})[0])
    portfolio = infl.portfolio_real_return(real_results)

    return InvestmentSummary(
        real_return_ars=PortfolioRealReturnOut(
            nominal_pct=portfolio.nominal_pct,
            inflation_pct=portfolio.inflation_pct,
            real_pct=portfolio.real_pct,
            estimated=portfolio.estimated,
            included_count=portfolio.included_count,
            excluded_count=portfolio.excluded_count,
        )
        if portfolio
        else None,
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

import logging
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Mapping, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today
from app.modules.ajustes.models import UserPreference
from app.modules.finanzas.models import Transaction
from app.modules.finanzas.repository import TransactionRepository
from app.modules.finanzas.schemas import TransactionCreate
from app.modules.finanzas.service import FinanzasService
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
    MAX_DATE,
    PortfolioRealReturnOut,
    ProjectionOut,
    RatesOut,
    RealReturnOut,
    RenewalChainOut,
    RenewalTermOut,
    RenewFixedTermIn,
    RenewMode,
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

logger = logging.getLogger(__name__)

#: Argentina: el mercado de la app. Se usa cuando el cliente no mando el offset.
DEFAULT_TZ_OFFSET_MINUTES = -180
RENEWAL_CHAIN_MAX = 100

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


def _unprocessable(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)


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
    inv: Investment,
    today: date,
    series: Optional[Mapping[date, Decimal]] = None,
    renewed_to_id: Optional[str] = None,
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
        renewed_from_id=inv.renewed_from_id,
        renewed_to_id=renewed_to_id,
        can_renew=(
            inv.asset_type == FIXED_TERM
            and inv.status == "active"
            and val.days_to_maturity is not None
            and val.days_to_maturity <= 0
            and renewed_to_id is None
        ),
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

        if (
            changes.get("status") == "active"
            and investment.status == "closed"
            and investment.id in (await self.repo.renewal_map(investment.user_id))
        ):
            # Reabrirlo sumaria el mismo capital dos veces (el viejo y su renovacion).
            raise _unprocessable("Este plazo fijo ya se renovó: no se puede reabrir")

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

    # ── Renovacion de plazo fijo ────────────────────────────────────────────

    async def renewal_map(self, user_id: str) -> dict[str, str]:
        return await self.repo.renewal_map(user_id)

    async def renew(
        self, investment: Investment, data: RenewFixedTermIn
    ) -> tuple[Investment, Investment, Optional[str]]:
        """Cierra un plazo fijo vencido y crea su renovacion, todo en una
        transaccion. Devuelve (cerrado, nuevo, id del ingreso por el interes)."""
        user_id = investment.user_id
        offset = (
            data.timezone_offset_minutes
            if data.timezone_offset_minutes is not None
            else investment.timezone_offset_minutes
            if investment.timezone_offset_minutes is not None
            else DEFAULT_TZ_OFFSET_MINUTES
        )
        today = local_today(offset)

        if investment.asset_type != FIXED_TERM:
            raise _unprocessable("Solo se pueden renovar los plazos fijos")
        # Antes de mirar el estado: un reintento (cola offline) de una renovacion
        # ya hecha tiene que dar 409 y no 422 por "cerrado".
        if investment.id in (await self.repo.renewal_map(user_id)):
            raise HTTPException(status.HTTP_409_CONFLICT, "Este plazo fijo ya se renovó")
        if investment.status != "active":
            raise _unprocessable("Este plazo fijo ya está cerrado")
        if investment.maturity_date is None or investment.maturity_date > today:
            raise _unprocessable("Todavía no venció: se puede renovar desde el día del vencimiento")

        start = data.start_date or today
        if start < investment.maturity_date or start > today:
            raise _unprocessable(
                "El inicio de la renovación tiene que estar entre el vencimiento anterior y hoy"
            )
        if data.maturity_date is not None:
            maturity = data.maturity_date
            if data.term_days is not None and (maturity - start).days != data.term_days:
                raise _unprocessable("El plazo en días no coincide con la fecha de vencimiento")
        else:
            maturity = start + timedelta(days=data.term_days)
        if maturity <= start:
            raise _unprocessable("El vencimiento tiene que ser posterior al inicio")
        if maturity > MAX_DATE:
            raise _unprocessable("El vencimiento no puede ser posterior a 2100")

        invested = round2(to_decimal(investment.invested_amount))
        fixed_term = valuate(investment, today).fixed_term
        if fixed_term is None:
            raise _unprocessable("Este plazo fijo no tiene TNA o fechas para calcular el cobro")
        computed = fixed_term.amount_at_maturity
        collected = round2(data.amount_collected) if data.amount_collected is not None else computed
        principal_only = data.mode == RenewMode.PRINCIPAL_ONLY
        if principal_only:
            if collected < invested:
                raise _unprocessable("El monto cobrado no puede ser menor al capital: el interés sería negativo")
            new_invested = invested
        else:
            if collected <= 0:
                raise _unprocessable("El monto cobrado tiene que ser mayor a 0")
            new_invested = collected

        interest = collected - invested
        income_tx = None
        if principal_only and data.register_interest_income and interest > 0:
            income_tx = await self._interest_transaction(investment, data, interest, start)

        closed_id, name = investment.id, investment.name
        try:
            investment.status = "closed"
            investment.current_value = collected
            investment.value_updated_at = datetime.now(timezone.utc)
            renewed = Investment(
                user_id=user_id,
                asset_type=FIXED_TERM,
                name=investment.name,
                currency=investment.currency,
                invested_amount=new_invested,
                interest_rate_tna=data.interest_rate_tna,
                start_date=start,
                maturity_date=maturity,
                institution=investment.institution,
                notes=investment.notes,
                status="active",
                notify_maturity=investment.notify_maturity,
                timezone_offset_minutes=investment.timezone_offset_minutes
                if data.timezone_offset_minutes is None
                else data.timezone_offset_minutes,
                renewed_from_id=closed_id,
            )
            self.db.add(renewed)
            if income_tx is not None:
                self.db.add(income_tx)
            await self.db.flush()
            await self.db.commit()
        except IntegrityError:
            # La unica de `renewed_from_id` cortó una renovacion simultanea.
            await self.db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, "Este plazo fijo ya se renovó")
        except Exception:
            await self.db.rollback()
            raise
        await self.db.refresh(investment)
        await self.db.refresh(renewed)
        logger.info("Plazo fijo %s (%s) renovado", closed_id, name)
        return investment, renewed, income_tx.id if income_tx is not None else None

    async def _interest_transaction(
        self, investment: Investment, data: RenewFixedTermIn, interest: Decimal, start: date
    ) -> Transaction:
        finance = FinanzasService(self.db)
        user_id = investment.user_id
        await finance._ensure_own_category(user_id, data.income_category_id)
        bank = None
        if data.income_bank_account_id is not None:
            bank = await finance.bank_account_repo.get_by_id(data.income_bank_account_id, user_id)
            if bank is None:
                raise HTTPException(status_code=404, detail="Cuenta no encontrada")
        tx_data = TransactionCreate(
            amount=interest,
            currency=investment.currency,
            type="income",
            transaction_date=start,
            bank_entity_name=(bank.bank_name or bank.name) if bank else "",
            account_type=bank.account_type if bank else "cash",
            account_last4=bank.last4 if bank else "",
            payment_method=data.income_payment_method,
            product_name=f"Interés plazo fijo: {investment.name}"[:255],
            merchant_name=investment.institution or "",
            category_id=UUID(data.income_category_id) if data.income_category_id else None,
        )
        tx = await finance.build_transaction(user_id, tx_data)
        tx.id = str(uuid4())
        return tx

    async def renewals(self, investment: Investment) -> RenewalChainOut:
        """La cadena de renovaciones que contiene `investment`, de la mas vieja
        a la mas nueva (tope 100)."""
        user_id = investment.user_id
        forward = await self.repo.renewal_map(user_id)  # {renovada: renovacion}
        backward = {new: old for old, new in forward.items()}
        chain = [investment.id]
        seen = {investment.id}
        cursor = investment.id
        while cursor in backward and backward[cursor] not in seen and len(chain) < RENEWAL_CHAIN_MAX:
            cursor = backward[cursor]
            seen.add(cursor)
            chain.insert(0, cursor)
        cursor = investment.id
        while cursor in forward and forward[cursor] not in seen and len(chain) < RENEWAL_CHAIN_MAX:
            cursor = forward[cursor]
            seen.add(cursor)
            chain.append(cursor)
        rows = await self.repo.get_many(user_id, chain)

        items: list[RenewalTermOut] = []
        accumulated = ZERO
        for inv_id in chain:
            inv = rows.get(inv_id)
            if inv is None:
                continue
            invested = round2(to_decimal(inv.invested_amount))
            ft = None
            if inv.interest_rate_tna is not None and inv.start_date and inv.maturity_date:
                if inv.maturity_date > inv.start_date:
                    ft = valuate(inv, inv.maturity_date).fixed_term
            if inv.status == "closed" and inv.current_value is not None:
                at_maturity = round2(to_decimal(inv.current_value))
                interest = at_maturity - invested
                accumulated += interest
            elif ft is not None:
                at_maturity, interest = ft.amount_at_maturity, ft.interest_total
            else:
                at_maturity, interest = None, None
            items.append(
                RenewalTermOut(
                    id=inv.id,
                    name=inv.name,
                    status=inv.status,
                    start_date=inv.start_date,
                    maturity_date=inv.maturity_date,
                    term_days=ft.term_days if ft else None,
                    invested_amount=invested,
                    interest_rate_tna=to_decimal(inv.interest_rate_tna),
                    amount_at_maturity=at_maturity,
                    interest=interest,
                    renewed_from_id=inv.renewed_from_id,
                )
            )
        return RenewalChainOut(
            items=items, accumulated_interest=round2(accumulated), currency=investment.currency
        )

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

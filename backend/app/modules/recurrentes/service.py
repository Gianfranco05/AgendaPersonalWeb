"""Servicio de movimientos recurrentes.

La pieza central es `materialize`: convierte las fechas vencidas de una
plantilla en transacciones (o pendientes de confirmacion) de forma atomica e
idempotente. Todo ocurre en UNA transaccion de base de datos:

1. se calculan las fechas debidas;
2. compare-and-set del cursor (`next_occurrence_date`): si otro worker o una
   edicion lo movio antes, esta llamada no hace nada;
3. se insertan las ocurrencias (restriccion unica por plantilla y fecha) y las
   transacciones;
4. `commit`. Si algo falla, se revierte todo, cursor incluido, y el proximo
   ciclo reintenta.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finanzas.models import BankAccount, Transaction
from app.modules.finanzas.schemas import TransactionCreate, TransactionResponse
from app.modules.finanzas.service import FinanzasService
from app.modules.inversiones.valuation import round2, to_decimal
from app.modules.recurrentes import rules
from app.modules.recurrentes.models import RecurringOccurrence, RecurringTransaction
from app.modules.recurrentes.repository import RecurringRepository
from app.modules.recurrentes.schemas import (
    MAX_DATE,
    ConfirmIn,
    OccurrenceOut,
    PreviewIn,
    PreviewOut,
    RecurringCreate,
    RecurringDetailOut,
    RecurringOut,
    RecurringUpdate,
    UpcomingItem,
    UpcomingOut,
    UpcomingTotal,
)

logger = logging.getLogger(__name__)

#: Recuperacion tras una caida del server: ocurrencias de los ultimos 62 dias,
#: hasta 62 por plantilla y ciclo.
CATCH_UP_DAYS = 62
CATCH_UP_MAX = 62
#: "Registrar tambien las anteriores" al crear: inicio hasta 366 dias atras y
#: hasta 120 movimientos.
BACKFILL_MAX_DAYS = 366
BACKFILL_MAX = 120
PREVIEW_COUNT = 5
DETAIL_NEXT_DATES = 3
DETAIL_RECENT = 12
UPCOMING_MAX_ITEMS = 300

RULE_KEYS = (
    "frequency",
    "interval_count",
    "weekday",
    "day_of_month",
    "month_of_year",
)

# Campos que un PUT con `null` no puede borrar: el `null` se ignora.
_REQUIRED_FIELDS = {
    "type",
    "name",
    "currency",
    "account_type",
    "payment_method",
    "merchant_name",
    "merchant_category",
    "frequency",
    "interval_count",
    "start_date",
    "requires_confirmation",
    "timezone_offset_minutes",
    "notify",
}


def _unprocessable(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)


def rule_of(rec: RecurringTransaction) -> rules.Rule:
    return rules.Rule(
        rec.frequency, rec.interval_count, rec.weekday, rec.day_of_month, rec.month_of_year
    )


@dataclass
class Generated:
    """Lo que `materialize` creo, con lo necesario para armar la push."""

    recurrence_id: str
    user_id: str
    name: str
    type: str
    currency: str
    notify: bool
    kind: str  # generated | pending
    amount: Optional[Decimal]
    occurrence_id: str
    occurrence_date: date
    transaction_id: Optional[str] = None
    bank_label: str = ""


@dataclass
class MaterializeResult:
    items: list[Generated] = field(default_factory=list)
    skipped_old: bool = False


def state_of(rec: RecurringTransaction) -> str:
    if rec.status == "paused":
        return "paused"
    return "finished" if rec.next_occurrence_date is None else "active"


def to_out(
    rec: RecurringTransaction,
    pending_count: int = 0,
    last_amount: Optional[Decimal] = None,
    cls=RecurringOut,
    **extra,
):
    return cls(
        id=rec.id,
        type=rec.type,
        name=rec.name,
        description=rec.description,
        notes=rec.notes,
        amount=to_decimal(rec.amount),
        currency=rec.currency,
        category_id=rec.category_id,
        bank_account_id=rec.bank_account_id,
        account_type=rec.account_type,
        payment_method=rec.payment_method,
        merchant_name=rec.merchant_name,
        merchant_category=rec.merchant_category,
        frequency=rec.frequency,
        interval_count=rec.interval_count,
        weekday=rec.weekday,
        day_of_month=rec.day_of_month,
        month_of_year=rec.month_of_year,
        start_date=rec.start_date,
        end_date=rec.end_date,
        anchor_date=rec.anchor_date,
        next_occurrence_date=rec.next_occurrence_date,
        last_occurrence_date=rec.last_occurrence_date,
        status=rec.status,
        paused_at=rec.paused_at,
        requires_confirmation=rec.requires_confirmation,
        notify=rec.notify,
        timezone_offset_minutes=rec.timezone_offset_minutes,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
        state=state_of(rec),
        rule_label=rules.rule_label(rule_of(rec)),
        pending_count=pending_count,
        last_amount=last_amount,
        **extra,
    )


def occurrence_out(
    occ: RecurringOccurrence,
    rec: Optional[RecurringTransaction] = None,
    transaction: Optional[Transaction] = None,
) -> OccurrenceOut:
    return OccurrenceOut(
        id=occ.id,
        recurrence_id=occ.recurrence_id,
        occurrence_date=occ.occurrence_date,
        status=occ.status,
        suggested_amount=to_decimal(occ.suggested_amount),
        transaction_id=occ.transaction_id,
        resolved_at=occ.resolved_at,
        created_at=occ.created_at,
        name=rec.name if rec else None,
        type=rec.type if rec else None,
        currency=rec.currency if rec else None,
        transaction=TransactionResponse.model_validate(transaction) if transaction else None,
    )


class RecurringService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RecurringRepository(db)
        self.finance = FinanzasService(db)

    # ── Validaciones ────────────────────────────────────────────────────────

    async def _ensure_refs(
        self, user_id: str, category_id: Optional[str], bank_account_id: Optional[str]
    ) -> None:
        """404 si la categoria o la cuenta no existen o son de otro usuario."""
        await self.finance._ensure_own_category(user_id, category_id)
        if bank_account_id is not None:
            if await self.finance.bank_account_repo.get_by_id(bank_account_id, user_id) is None:
                raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    # ── Lecturas ────────────────────────────────────────────────────────────

    async def get(self, recurrence_id: str, user_id: str) -> Optional[RecurringTransaction]:
        return await self.repo.get(recurrence_id, user_id)

    async def list_out(self, user_id: str, status_filter: str = "all") -> list[RecurringOut]:
        items = await self.repo.list(user_id, status_filter)
        pending = await self.repo.pending_counts(user_id)
        last = await self.repo.last_amounts(user_id)
        return [to_out(r, pending.get(r.id, 0), last.get(r.id)) for r in items]

    async def out(self, rec: RecurringTransaction) -> RecurringOut:
        pending = (await self.repo.pending_counts(rec.user_id)).get(rec.id, 0)
        last = (await self.repo.last_amounts(rec.user_id)).get(rec.id)
        return to_out(rec, pending, last)

    async def detail(self, rec: RecurringTransaction, today: date) -> RecurringDetailOut:
        pending = (await self.repo.pending_counts(rec.user_id)).get(rec.id, 0)
        last = (await self.repo.last_amounts(rec.user_id)).get(rec.id)
        recent = await self.repo.recent_occurrences(rec.id, rec.user_id, DETAIL_RECENT)
        next_dates: list[date] = []
        if rec.status == "active" and rec.next_occurrence_date is not None:
            next_dates = rules.occurrences_between(
                rule_of(rec),
                rec.anchor_date,
                max(rec.next_occurrence_date, today),
                MAX_DATE,
                rec.end_date,
                limit=DETAIL_NEXT_DATES,
            )
        return to_out(
            rec,
            pending,
            last,
            cls=RecurringDetailOut,
            recent_occurrences=[occurrence_out(o, rec) for o in recent],
            next_dates=next_dates,
        )

    def preview(self, data: PreviewIn, today: date) -> PreviewOut:
        rule = rules.normalize_rule(data.rule())
        anchor = rules.compute_anchor(rule, data.start_date)
        first = data.start_date if data.generate_past else max(data.start_date, today)
        dates = rules.occurrences_between(
            rule, anchor, first, MAX_DATE, data.end_date, limit=PREVIEW_COUNT
        )
        return PreviewOut(anchor_date=anchor, dates=dates)

    async def upcoming(self, user_id: str, today: date, days: int) -> UpcomingOut:
        horizon = today + timedelta(days=days)
        items: list[UpcomingItem] = []
        for rec in await self.repo.list(user_id, "active"):
            if rec.next_occurrence_date is None:
                continue
            for d in rules.occurrences_between(
                rule_of(rec),
                rec.anchor_date,
                max(rec.next_occurrence_date, today),
                horizon,
                rec.end_date,
                limit=UPCOMING_MAX_ITEMS,
            ):
                items.append(
                    UpcomingItem(
                        recurrence_id=rec.id,
                        date=d,
                        name=rec.name,
                        type=rec.type,
                        amount=to_decimal(rec.amount),
                        currency=rec.currency,
                        requires_confirmation=rec.requires_confirmation,
                    )
                )
        items.sort(key=lambda i: (i.date, i.name))
        items = items[:UPCOMING_MAX_ITEMS]
        totals: dict[tuple[str, str], Decimal] = {}
        for item in items:
            if item.amount is not None:
                key = (item.type, item.currency)
                totals[key] = totals.get(key, Decimal("0")) + item.amount
        return UpcomingOut(
            days=days,
            items=items,
            totals=[
                UpcomingTotal(type=t, currency=c, total=round2(v))
                for (t, c), v in sorted(totals.items())
            ],
        )

    async def pending_out(self, user_id: str, pending_only: bool = True) -> list[OccurrenceOut]:
        occurrences = await self.repo.list_occurrences(user_id, pending_only)
        recs = {r.id: r for r in await self.repo.list(user_id, "all")}
        return [occurrence_out(o, recs.get(o.recurrence_id)) for o in occurrences]

    # ── Generacion ──────────────────────────────────────────────────────────

    async def _build_transaction(
        self,
        rec: RecurringTransaction,
        occurrence_date: date,
        amount: Decimal,
        notes: Optional[str],
        bank: Optional[BankAccount],
        category_ok: bool,
    ) -> Transaction:
        if bank is not None:
            bank_entity, account_type, last4 = (bank.bank_name or bank.name), bank.account_type, bank.last4
        else:
            bank_entity, account_type, last4 = "", rec.account_type, ""
        data = TransactionCreate(
            amount=amount,
            currency=rec.currency,
            type=rec.type,
            transaction_date=occurrence_date,
            bank_entity_name=bank_entity,
            account_type=account_type,
            account_last4=last4,
            payment_method=rec.payment_method,
            product_name=rec.name,
            product_description=rec.description,
            merchant_name=rec.merchant_name,
            merchant_category=rec.merchant_category,
            notes=notes,
            category_id=UUID(rec.category_id) if (rec.category_id and category_ok) else None,
        )
        tx = await self.finance.build_transaction(rec.user_id, data)
        tx.id = str(uuid4())
        tx.is_recurring = True
        tx.recurring_parent_id = rec.id
        return tx

    async def _refs_state(self, rec: RecurringTransaction) -> tuple[Optional[BankAccount], bool]:
        """(cuenta propia o None, la categoria sigue existiendo). Si se borro
        la cuenta o la categoria a espaldas de la plantilla, se genera igual,
        sin ellas, en vez de fallar para siempre."""
        bank = None
        if rec.bank_account_id:
            bank = await self.finance.bank_account_repo.get_by_id(rec.bank_account_id, rec.user_id)
        category_ok = True
        if rec.category_id:
            category_ok = (
                await self.finance.category_repo.get_by_id(rec.category_id, rec.user_id)
            ) is not None
        return bank, category_ok

    async def materialize(
        self,
        rec: RecurringTransaction,
        today: date,
        *,
        window_days: Optional[int] = CATCH_UP_DAYS,
        max_count: int = CATCH_UP_MAX,
    ) -> MaterializeResult:
        """Genera lo vencido hasta `today` (fecha local del usuario)."""
        result = MaterializeResult()
        if rec.status != "active" or rec.next_occurrence_date is None:
            return result
        cursor = rec.next_occurrence_date
        if cursor > today:
            return result

        # Todo lo que se necesita de `rec` se copia ahora: un rollback expira
        # el objeto y en async leerlo despues revienta (lazy load).
        rec_id, user_id = rec.id, rec.user_id
        rule, anchor, end = rule_of(rec), rec.anchor_date, rec.end_date

        floor = cursor
        if window_days is not None:
            # "Ultimos 62 dias" contando hoy: como mucho 62 fechas de una diaria.
            window_start = today - timedelta(days=window_days - 1)
            if cursor < window_start:
                floor = window_start
                result.skipped_old = True
                logger.warning(
                    "Recurrente %s: se saltean las ocurrencias anteriores al %s (caida larga)",
                    rec_id,
                    window_start,
                )
        start = rules.first_on_or_after(rule, anchor, floor)[1]
        limit_date = min(today, end) if end is not None else today
        dates: list[date] = []
        for d in rules.iter_from(rule, anchor, start, limit_date):
            dates.append(d)
            if len(dates) >= max_count:
                break
        if dates:
            new_cursor = rules.next_cursor(rule, anchor, dates[-1], end)
            last = dates[-1]
        else:
            new_cursor = start if (end is None or start <= end) else None
            last = None
        if new_cursor == cursor:
            return result
        # Fechas que ya tienen su ocurrencia (p. ej. el cursor quedo apuntando a
        # un dia ya procesado): se avanza el cursor sin volver a generarlas. Evita
        # que la restriccion unica trabe la plantilla en un ciclo de reintentos.
        already = await self.repo.occurrence_dates(rec_id, user_id, dates)
        to_create = [d for d in dates if d not in already]

        try:
            if not await self.repo.advance_cursor(rec_id, user_id, cursor, new_cursor, last):
                # Otro worker (o una edicion) se adelanto: no hay nada que hacer.
                await self.db.rollback()
                await self.db.refresh(rec)
                return MaterializeResult()

            if to_create:
                await self.db.refresh(rec)
                bank, category_ok = await self._refs_state(rec)
                suggested = None
                if rec.requires_confirmation:
                    suggested = await self.repo.last_confirmed_amount(rec_id, user_id)
                    if suggested is None:
                        suggested = to_decimal(rec.amount)
                bank_label = (bank.bank_name or bank.name) if bank is not None else ""
                for d in to_create:
                    occ = RecurringOccurrence(
                        id=str(uuid4()),
                        user_id=user_id,
                        recurrence_id=rec_id,
                        occurrence_date=d,
                        status="pending" if rec.requires_confirmation else "generated",
                        suggested_amount=suggested if rec.requires_confirmation else None,
                    )
                    tx = None
                    if not rec.requires_confirmation:
                        tx = await self._build_transaction(
                            rec, d, to_decimal(rec.amount), rec.notes, bank, category_ok
                        )
                        self.db.add(tx)
                        occ.transaction_id = tx.id
                    self.db.add(occ)
                    result.items.append(
                        Generated(
                            recurrence_id=rec_id,
                            user_id=user_id,
                            name=rec.name,
                            type=rec.type,
                            currency=rec.currency,
                            notify=rec.notify,
                            kind="pending" if rec.requires_confirmation else "generated",
                            amount=suggested if rec.requires_confirmation else to_decimal(rec.amount),
                            occurrence_id=occ.id,
                            occurrence_date=d,
                            transaction_id=tx.id if tx else None,
                            bank_label=bank_label,
                        )
                    )
                await self.db.flush()
            await self.db.commit()
        except IntegrityError:
            # La restriccion unica cortó un doble procesamiento: se revierte todo.
            await self.db.rollback()
            logger.warning("Recurrente %s: ocurrencia duplicada, se revierte el ciclo", rec_id)
            await self.db.refresh(rec)
            return MaterializeResult()
        except Exception:
            await self.db.rollback()
            raise
        await self.db.refresh(rec)
        return result

    # ── Alta / edicion ──────────────────────────────────────────────────────

    async def create(self, user_id: str, data: RecurringCreate) -> RecurringTransaction:
        await self._ensure_refs(user_id, data.category_id, data.bank_account_id)
        now = rules.utc_now()
        today = rules.local_today(now, data.timezone_offset_minutes)
        rule = rules.normalize_rule(data.rule())
        anchor = rules.compute_anchor(rule, data.start_date)

        window: Optional[int] = CATCH_UP_DAYS
        max_count = CATCH_UP_MAX
        if data.generate_past and data.start_date < today:
            if data.start_date < today - timedelta(days=BACKFILL_MAX_DAYS):
                raise _unprocessable("El inicio no puede ser de hace más de un año para registrar los anteriores")
            past = rules.occurrences_between(
                rule, anchor, data.start_date, today, data.end_date, limit=BACKFILL_MAX + 1
            )
            if len(past) > BACKFILL_MAX:
                raise _unprocessable(
                    f"Son demasiados movimientos para registrar de una vez (máx. {BACKFILL_MAX})"
                )
            cursor = rules.cursor_from(rule, anchor, data.start_date, data.end_date)
            window, max_count = None, BACKFILL_MAX
        else:
            cursor = rules.cursor_from(
                rule, anchor, max(data.start_date, today), data.end_date
            )

        rec = RecurringTransaction(
            id=str(uuid4()),
            user_id=user_id,
            type=data.type,
            name=data.name,
            description=data.description,
            notes=data.notes,
            amount=round2(data.amount) if data.amount is not None else None,
            currency=data.currency,
            category_id=data.category_id,
            bank_account_id=data.bank_account_id,
            account_type=data.account_type,
            payment_method=data.payment_method,
            merchant_name=data.merchant_name,
            merchant_category=data.merchant_category,
            frequency=rule.frequency,
            interval_count=rule.interval_count,
            weekday=rule.weekday,
            day_of_month=rule.day_of_month,
            month_of_year=rule.month_of_year,
            start_date=data.start_date,
            end_date=data.end_date,
            anchor_date=anchor,
            next_occurrence_date=cursor,
            status="active",
            requires_confirmation=data.requires_confirmation,
            notify=data.notify,
            timezone_offset_minutes=data.timezone_offset_minutes,
        )
        self.repo.add(rec)
        await self.db.commit()
        await self.db.refresh(rec)
        await self.materialize(rec, today, window_days=window, max_count=max_count)
        return rec

    async def update(self, rec: RecurringTransaction, data: RecurringUpdate) -> RecurringTransaction:
        changes = data.model_dump(exclude_unset=True)
        for key in _REQUIRED_FIELDS:
            if key in changes and changes[key] is None:
                del changes[key]
        user_id = rec.user_id

        await self._ensure_refs(
            user_id,
            changes.get("category_id") if "category_id" in changes else None,
            changes.get("bank_account_id") if "bank_account_id" in changes else None,
        )

        # Reglas cruzadas sobre el estado resultante, no sobre el payload.
        amount = round2(changes["amount"]) if changes.get("amount") is not None else (
            None if "amount" in changes else to_decimal(rec.amount)
        )
        requires = changes.get("requires_confirmation", rec.requires_confirmation)
        if amount is None and not requires:
            raise _unprocessable("Ingresá el monto o activá «Confirmar el monto antes de registrar»")
        if amount is not None and amount <= 0:
            raise _unprocessable("El monto debe ser mayor a 0")
        changes["amount"] = amount

        start = changes.get("start_date", rec.start_date)
        end = changes["end_date"] if "end_date" in changes else rec.end_date
        if end is not None and end < start:
            raise _unprocessable("La fecha de fin no puede ser anterior a la de inicio")

        old_rule = rule_of(rec)
        merged = rules.Rule(
            changes.get("frequency", rec.frequency),
            changes.get("interval_count", rec.interval_count),
            changes.get("weekday", rec.weekday),
            changes.get("day_of_month", rec.day_of_month),
            changes.get("month_of_year", rec.month_of_year),
        )
        try:
            rules.validate_rule(merged)
        except ValueError as exc:
            raise _unprocessable(str(exc))
        new_rule = rules.normalize_rule(merged)
        rule_changed = new_rule != old_rule or start != rec.start_date

        for key in RULE_KEYS:
            changes.pop(key, None)
        for key, value in changes.items():
            setattr(rec, key, value)
        rec.frequency = new_rule.frequency
        rec.interval_count = new_rule.interval_count
        rec.weekday = new_rule.weekday
        rec.day_of_month = new_rule.day_of_month
        rec.month_of_year = new_rule.month_of_year

        today = rules.local_today(rules.utc_now(), rec.timezone_offset_minutes)
        if rule_changed:
            floor = max(today, start)
            if rec.last_occurrence_date is not None:
                floor = max(floor, rec.last_occurrence_date + timedelta(days=1))
            rec.anchor_date = rules.compute_anchor(new_rule, start, floor)
            rec.next_occurrence_date = rules.cursor_from(new_rule, rec.anchor_date, floor, end)
        elif "end_date" in changes:
            if rec.next_occurrence_date is None:
                # Terminada: una fecha de fin posterior la revive desde lo ultimo procesado.
                if rec.last_occurrence_date is not None:
                    rec.next_occurrence_date = rules.next_cursor(
                        new_rule, rec.anchor_date, rec.last_occurrence_date, end
                    )
                else:
                    rec.next_occurrence_date = rules.cursor_from(
                        new_rule, rec.anchor_date, start, end
                    )
            elif end is not None and rec.next_occurrence_date > end:
                rec.next_occurrence_date = None

        await self.db.commit()
        await self.db.refresh(rec)
        if rec.status == "active":
            await self.materialize(rec, today)
        return rec

    async def pause(self, rec: RecurringTransaction, offset: Optional[int]) -> RecurringTransaction:
        if offset is not None:
            rec.timezone_offset_minutes = offset
        if rec.status != "paused":
            rec.status = "paused"
            rec.paused_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(rec)
        return rec

    async def resume(self, rec: RecurringTransaction, offset: Optional[int]) -> RecurringTransaction:
        if offset is not None:
            rec.timezone_offset_minutes = offset
        if rec.status == "paused":
            today = rules.local_today(rules.utc_now(), rec.timezone_offset_minutes)
            rec.status = "active"
            rec.paused_at = None
            # Lo que cayo durante la pausa no se genera: el cursor salta a hoy
            # (o al dia siguiente de lo ultimo procesado, si hoy ya se registro).
            floor = today
            if rec.last_occurrence_date is not None:
                floor = max(floor, rec.last_occurrence_date + timedelta(days=1))
            rec.next_occurrence_date = rules.cursor_from(
                rule_of(rec), rec.anchor_date, floor, rec.end_date
            )
            await self.db.commit()
            await self.db.refresh(rec)
            await self.materialize(rec, today)
        else:
            await self.db.commit()
            await self.db.refresh(rec)
        return rec

    async def delete(self, rec: RecurringTransaction) -> None:
        await self.repo.delete(rec)

    # ── Pendientes ──────────────────────────────────────────────────────────

    async def _occurrence_response(
        self, occ: RecurringOccurrence, rec: Optional[RecurringTransaction]
    ) -> OccurrenceOut:
        tx = None
        if occ.transaction_id:
            tx = (await self.repo.transactions_by_id(occ.user_id, [occ.transaction_id])).get(
                occ.transaction_id
            )
        return occurrence_out(occ, rec, tx)

    async def confirm(self, user_id: str, occurrence_id: str, data: ConfirmIn) -> OccurrenceOut:
        occ = await self.repo.get_occurrence(occurrence_id, user_id)
        if occ is None:
            raise HTTPException(status_code=404, detail="Movimiento pendiente no encontrado")
        rec = await self.repo.get(occ.recurrence_id, user_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="Movimiento pendiente no encontrado")
        if occ.status == "confirmed":
            return await self._occurrence_response(occ, rec)
        if occ.status == "skipped":
            raise HTTPException(status_code=409, detail="Este movimiento ya se salteó")
        if occ.status == "generated":
            raise HTTPException(status_code=409, detail="Este movimiento ya se registró solo")

        occ_id, rec_id = occ.id, rec.id
        try:
            claimed = await self.repo.claim_occurrence_status(
                occ_id, user_id, "confirmed", datetime.now(timezone.utc)
            )
            if not claimed:
                await self.db.rollback()
                return await self._resolved_again(user_id, occ_id, rec_id, "confirmed")
            await self.db.refresh(rec)
            bank, category_ok = await self._refs_state(rec)
            tx = await self._build_transaction(
                rec,
                data.transaction_date or occ.occurrence_date,
                round2(data.amount),
                data.notes if data.notes is not None else rec.notes,
                bank,
                category_ok,
            )
            self.db.add(tx)
            await self.db.flush()
            await self.db.execute(
                update(RecurringOccurrence)
                .where(RecurringOccurrence.id == occ_id)
                .values(transaction_id=tx.id)
                .execution_options(synchronize_session=False)
            )
            if data.timezone_offset_minutes is not None:
                rec.timezone_offset_minutes = data.timezone_offset_minutes
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return await self._reload_occurrence(user_id, occ_id, rec_id)

    async def skip(self, user_id: str, occurrence_id: str, offset: Optional[int]) -> OccurrenceOut:
        occ = await self.repo.get_occurrence(occurrence_id, user_id)
        if occ is None:
            raise HTTPException(status_code=404, detail="Movimiento pendiente no encontrado")
        rec = await self.repo.get(occ.recurrence_id, user_id)
        if occ.status == "skipped":
            return await self._occurrence_response(occ, rec)
        if occ.status in ("confirmed", "generated"):
            raise HTTPException(status_code=409, detail="Este movimiento ya se registró")
        occ_id, rec_id = occ.id, occ.recurrence_id
        claimed = await self.repo.claim_occurrence_status(
            occ_id, user_id, "skipped", datetime.now(timezone.utc)
        )
        if not claimed:
            await self.db.rollback()
            return await self._resolved_again(user_id, occ_id, rec_id, "skipped")
        if offset is not None and rec is not None:
            rec.timezone_offset_minutes = offset
        await self.db.commit()
        return await self._reload_occurrence(user_id, occ_id, rec_id)

    async def _reload_occurrence(self, user_id: str, occ_id: str, rec_id: str) -> OccurrenceOut:
        occ = await self.repo.get_occurrence(occ_id, user_id)
        await self.db.refresh(occ)
        rec = await self.repo.get(rec_id, user_id)
        return await self._occurrence_response(occ, rec)

    async def _resolved_again(
        self, user_id: str, occ_id: str, rec_id: str, wanted: str
    ) -> OccurrenceOut:
        """Perdio la carrera contra otra confirmacion/salteo: si el resultado es
        el mismo que se pedia es un reintento (200), si no, un conflicto."""
        occ = await self.repo.get_occurrence(occ_id, user_id)
        if occ is None:
            raise HTTPException(status_code=404, detail="Movimiento pendiente no encontrado")
        await self.db.refresh(occ)
        if occ.status != wanted:
            raise HTTPException(status_code=409, detail="Este movimiento ya se resolvió")
        rec = await self.repo.get(rec_id, user_id)
        return await self._occurrence_response(occ, rec)

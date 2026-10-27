from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy import and_, case, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finanzas.models import Transaction
from app.modules.recurrentes.models import RecurringOccurrence, RecurringTransaction

R = RecurringTransaction
O = RecurringOccurrence


class RecurringRepository:
    """Toda consulta filtra por `user_id`: un id ajeno responde "no existe"."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Plantillas ──────────────────────────────────────────────────────────

    async def get(self, recurrence_id: str, user_id: str) -> Optional[R]:
        result = await self.db.execute(
            select(R)
            .where(and_(R.id == recurrence_id, R.user_id == user_id))
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def list(self, user_id: str, status: str = "all") -> Sequence[R]:
        query = select(R).where(R.user_id == user_id)
        if status != "all":
            query = query.where(R.status == status)
        # Activas primero, por proxima fecha (las terminadas, al final), y nombre.
        query = query.order_by(
            case((R.status == "active", 0), else_=1),
            case((R.next_occurrence_date.is_(None), 1), else_=0),
            R.next_occurrence_date,
            R.name,
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    def add(self, rec: R) -> None:
        self.db.add(rec)

    async def delete(self, rec: R) -> None:
        """Borra la plantilla y sus ocurrencias; las transacciones generadas se
        conservan y quedan desvinculadas (`recurring_parent_id = NULL`)."""
        await self.db.execute(
            update(Transaction)
            .where(
                and_(
                    Transaction.user_id == rec.user_id,
                    Transaction.recurring_parent_id == rec.id,
                )
            )
            .values(recurring_parent_id=None)
        )
        await self.db.execute(
            delete(O).where(and_(O.recurrence_id == rec.id, O.user_id == rec.user_id))
        )
        await self.db.execute(delete(R).where(and_(R.id == rec.id, R.user_id == rec.user_id)))
        await self.db.commit()

    async def list_due(self, utc_today: date) -> Sequence[R]:
        """Activas cuyo cursor puede estar vencido en algun huso horario (el
        "hoy" local va de un dia antes a uno despues del de UTC). El filtro fino
        por fecha y hora local se hace en Python."""
        from datetime import timedelta

        result = await self.db.execute(
            select(R).where(
                and_(
                    R.status == "active",
                    R.next_occurrence_date.is_not(None),
                    R.next_occurrence_date <= utc_today + timedelta(days=1),
                )
            )
        )
        return result.scalars().all()

    async def advance_cursor(
        self,
        rec_id: str,
        user_id: str,
        old: date,
        new: Optional[date],
        last: Optional[date],
    ) -> bool:
        """Compare-and-set del cursor: True solo si esta llamada lo movio.
        Si otro worker (o una edicion) lo cambio antes, devuelve False."""
        values = {"next_occurrence_date": new}
        if last is not None:
            values["last_occurrence_date"] = last
        result = await self.db.execute(
            update(R)
            .where(
                and_(
                    R.id == rec_id,
                    R.user_id == user_id,
                    R.status == "active",
                    R.next_occurrence_date == old,
                )
            )
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1

    # ── Ocurrencias ─────────────────────────────────────────────────────────

    async def get_occurrence(self, occurrence_id: str, user_id: str) -> Optional[O]:
        result = await self.db.execute(
            select(O)
            .where(and_(O.id == occurrence_id, O.user_id == user_id))
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def list_occurrences(
        self, user_id: str, pending_only: bool = True, limit: int = 200
    ) -> Sequence[O]:
        query = select(O).where(O.user_id == user_id)
        if pending_only:
            query = query.where(O.status == "pending")
        query = query.order_by(O.occurrence_date, O.created_at).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def recent_occurrences(self, recurrence_id: str, user_id: str, limit: int = 12):
        result = await self.db.execute(
            select(O)
            .where(and_(O.recurrence_id == recurrence_id, O.user_id == user_id))
            .order_by(O.occurrence_date.desc())
            .limit(limit)
        )
        return result.scalars().all()

    def add_occurrence(self, occ: O) -> None:
        self.db.add(occ)

    async def claim_occurrence_status(
        self, occurrence_id: str, user_id: str, new_status: str, resolved_at: datetime
    ) -> bool:
        """CAS `pending -> confirmed/skipped`: True solo si esta llamada lo
        resolvio (repetirla, p. ej. desde la cola offline, devuelve False)."""
        result = await self.db.execute(
            update(O)
            .where(and_(O.id == occurrence_id, O.user_id == user_id, O.status == "pending"))
            .values(status=new_status, resolved_at=resolved_at)
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1

    async def last_confirmed_amount(self, recurrence_id: str, user_id: str) -> Optional[Decimal]:
        """Monto de la ultima ocurrencia confirmada (sugerencia del proximo pendiente)."""
        result = await self.db.execute(
            select(Transaction.amount)
            .join(O, O.transaction_id == Transaction.id)
            .where(
                and_(
                    O.recurrence_id == recurrence_id,
                    O.user_id == user_id,
                    O.status == "confirmed",
                )
            )
            .order_by(O.occurrence_date.desc(), O.resolved_at.desc())
            .limit(1)
        )
        value = result.scalar_one_or_none()
        return None if value is None else Decimal(str(value))

    async def pending_counts(self, user_id: str) -> dict[str, int]:
        result = await self.db.execute(
            select(O.recurrence_id, func.count())
            .where(and_(O.user_id == user_id, O.status == "pending"))
            .group_by(O.recurrence_id)
        )
        return {row[0]: row[1] for row in result.all()}

    async def last_amounts(self, user_id: str) -> dict[str, Decimal]:
        """Monto del ultimo movimiento generado/confirmado de cada plantilla."""
        latest = (
            select(O.recurrence_id.label("rid"), func.max(O.occurrence_date).label("d"))
            .where(
                and_(O.user_id == user_id, O.status.in_(("generated", "confirmed")))
            )
            .group_by(O.recurrence_id)
            .subquery()
        )
        result = await self.db.execute(
            select(O.recurrence_id, Transaction.amount)
            .join(latest, and_(O.recurrence_id == latest.c.rid, O.occurrence_date == latest.c.d))
            .join(Transaction, Transaction.id == O.transaction_id)
            .where(O.user_id == user_id)
        )
        return {row[0]: Decimal(str(row[1])) for row in result.all()}

    async def transactions_by_id(self, user_id: str, ids: Sequence[str]) -> dict[str, Transaction]:
        if not ids:
            return {}
        result = await self.db.execute(
            select(Transaction).where(
                and_(Transaction.user_id == user_id, Transaction.id.in_(ids))
            )
        )
        return {t.id: t for t in result.scalars().all()}

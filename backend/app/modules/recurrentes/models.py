from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    false,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class RecurringTransaction(Base):
    """Plantilla de un movimiento que se repite (sueldo, alquiler, Netflix...).

    La plantilla no es un movimiento: el scheduler del server crea la
    transaccion real (o un pendiente de confirmacion) el dia que toca. Los
    CHECK son validos tanto en SQLite como en Postgres. `interval_count` y no
    `interval` porque este ultimo es palabra clave de SQL.

    `anchor_date` es la primera ocurrencia de la regla vigente y la fecha k se
    calcula siempre desde ahi (ver `rules.py`); `next_occurrence_date` es el
    cursor: lo que todavia no se proceso. NULL = la regla termino (`end_date`).
    """

    __tablename__ = "recurring_transactions"
    __table_args__ = (
        CheckConstraint("amount IS NULL OR amount > 0", name="ck_recurring_amount_positive"),
        CheckConstraint(
            "amount IS NOT NULL OR requires_confirmation", name="ck_recurring_amount_or_confirm"
        ),
        CheckConstraint("interval_count >= 1", name="ck_recurring_interval_positive"),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date", name="ck_recurring_dates_order"
        ),
        CheckConstraint("status IN ('active', 'paused')", name="ck_recurring_status"),
        CheckConstraint(
            "frequency IN ('daily', 'weekly', 'monthly', 'yearly')", name="ck_recurring_frequency"
        ),
        Index("ix_recurring_user_status", "user_id", "status"),
        # Lo recorre el scheduler en cada ciclo.
        Index("ix_recurring_status_next", "status", "next_occurrence_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)

    type: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    #: NULL solo con `requires_confirmation` ("monto variable sin estimado").
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="ARS", server_default="ARS")

    category_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("categories.id"), nullable=True
    )
    bank_account_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("bank_accounts.id"), nullable=True
    )
    account_type: Mapped[str] = mapped_column(String(10), default="cash", server_default="cash")
    payment_method: Mapped[str] = mapped_column(
        String(20), default="cash", server_default="cash"
    )
    merchant_name: Mapped[str] = mapped_column(String(255), default="", server_default="")
    merchant_category: Mapped[str] = mapped_column(
        String(20), default="other", server_default="other"
    )

    frequency: Mapped[str] = mapped_column(String(10))
    interval_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    #: 0 = lunes ... 6 = domingo (`date.weekday()`). Solo semanal.
    weekday: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    day_of_month: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    month_of_year: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    anchor_date: Mapped[date] = mapped_column(Date)
    next_occurrence_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_occurrence_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    status: Mapped[str] = mapped_column(String(10), default="active", server_default="active")
    paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    requires_confirmation: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
    notify: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    #: Minutos al este de UTC, lo manda el cliente en cada escritura.
    timezone_offset_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RecurringOccurrence(Base):
    """Libro de lo que ya se proceso: una fila por (plantilla, fecha). La
    restriccion unica es la red de seguridad de la idempotencia y los
    `pending` son la cola de confirmaciones."""

    __tablename__ = "recurring_occurrences"
    __table_args__ = (
        UniqueConstraint("recurrence_id", "occurrence_date", name="uq_recurring_occurrence_date"),
        CheckConstraint(
            "status IN ('generated', 'pending', 'confirmed', 'skipped')",
            name="ck_recurring_occurrence_status",
        ),
        Index("ix_occurrences_user_status", "user_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    recurrence_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recurring_transactions.id"), index=True
    )
    occurrence_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10))
    suggested_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    transaction_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("transactions.id"), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

from uuid import uuid4
from datetime import date, datetime, time
from enum import Enum

from sqlalchemy import (
    String,
    Text,
    Boolean,
    Date,
    Time,
    Integer,
    ForeignKey,
    Numeric,
    DateTime,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.core.base import Base


class IsoText(TypeDecorator):
    """VARCHAR que guarda fechas/horas como texto ISO.

    `transaction_date` y `transaction_time` son String(10) (decision vieja que
    no se toca: cambiarla es una migracion de datos). El schema los entrega
    como `date`/`time`: SQLite los adapta solo, pero asyncpg rechaza un `date`
    para un parametro VARCHAR ("expected str, got date") — crear una
    transaccion o filtrar por fechas daba 500 en Postgres. Convertirlos aca
    cubre el insert, el update y los filtros `>=`/`<` de todos los repos.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, time):
            # %H:%M:%S: isoformat() con microsegundos pasa los 10 caracteres.
            return value.strftime("%H:%M:%S")
        return value


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        # "Movimientos de esta recurrencia" (filtro `recurrence_id`).
        Index("ix_transactions_recurring_parent_id", "recurring_parent_id"),
        # Deteccion de duplicados al importar (misma huella de fila).
        Index("ix_transactions_user_import_hash", "user_id", "import_row_hash"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)

    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="ARS")
    type: Mapped[str] = mapped_column(String(10))

    transaction_date: Mapped[str] = mapped_column(IsoText(10))
    transaction_time: Mapped[str] = mapped_column(IsoText(10), nullable=True)

    bank_entity_name: Mapped[str] = mapped_column(String(100), default="")
    account_type: Mapped[str] = mapped_column(String(10), default="cash")
    account_last4: Mapped[str] = mapped_column(String(4), default="")
    payment_method: Mapped[str] = mapped_column(String(20), default="cash")

    product_name: Mapped[str] = mapped_column(String(255))
    product_description: Mapped[str] = mapped_column(Text, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=True)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)

    merchant_name: Mapped[str] = mapped_column(String(255), default="")
    merchant_category: Mapped[str] = mapped_column(String(20), default="other")

    notes: Mapped[str] = mapped_column(Text, nullable=True)
    receipt_path: Mapped[str] = mapped_column(String(500), nullable=True)

    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurring_parent_id: Mapped[str] = mapped_column(String(36), nullable=True)

    #: Lote de importacion que creo este movimiento (None si es manual). La FK
    #: es SET NULL: borrar el lote no borra los movimientos.
    import_batch_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("import_batches.id", ondelete="SET NULL", name="fk_transactions_import_batch_id"),
        nullable=True,
    )
    import_row_hash: Mapped[str] = mapped_column(String(64), nullable=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("categories.id"), nullable=True
    )

    @property
    def recurrence_id(self) -> str | None:
        """Plantilla recurrente que genero este movimiento (None si es manual
        o si la plantilla se borro)."""
        return self.recurring_parent_id


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(7), default="#6366f1")
    icon: Mapped[str] = mapped_column(String(50), default="fa-folder")
    parent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("categories.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    bank_name: Mapped[str] = mapped_column(String(100), default="")
    account_type: Mapped[str] = mapped_column(String(10))
    account_number: Mapped[str] = mapped_column(String(20), default="")
    last4: Mapped[str] = mapped_column(String(4), default="")
    currency: Mapped[str] = mapped_column(String(3), default="ARS")
    balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("categories.id"))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    period: Mapped[str] = mapped_column(String(10), default="monthly")
    alert_threshold: Mapped[int] = mapped_column(Integer, default=80)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# Registra `import_batches` en Base.metadata junto con `transactions` (la FK
# apunta ahi): sin esto alembic/create_all no la verian si nadie la importa.
from app.modules.finanzas.transfer import models as _transfer_models  # noqa: E402,F401

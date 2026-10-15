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
    String,
    Text,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class Investment(Base):
    """Una posicion de inversion (plazo fijo, acciones, cripto, dolares...).

    Es el estado actual del activo, sin historial de compras/ventas: el usuario
    carga cuanto invirtio y, si quiere, cuanto vale hoy. Para el plazo fijo el
    valor se calcula solo (ver `valuation.py`).

    `asset_type` y `currency` se validan en el schema y no con un CHECK en la
    base, para poder sumar tipos/monedas sin migrar. Los demas CHECK son
    validos tanto en SQLite como en Postgres.
    """

    __tablename__ = "investments"
    __table_args__ = (
        CheckConstraint("invested_amount >= 0", name="ck_investments_invested_nonneg"),
        CheckConstraint(
            "current_value IS NULL OR current_value >= 0", name="ck_investments_value_nonneg"
        ),
        CheckConstraint(
            "quantity IS NULL OR quantity >= 0", name="ck_investments_quantity_nonneg"
        ),
        CheckConstraint(
            "interest_rate_tna IS NULL OR interest_rate_tna >= 0", name="ck_investments_tna_nonneg"
        ),
        CheckConstraint(
            "start_date IS NULL OR maturity_date IS NULL OR maturity_date >= start_date",
            name="ck_investments_dates_order",
        ),
        CheckConstraint("status IN ('active', 'closed')", name="ck_investments_status"),
        Index("ix_investments_user_status", "user_id", "status"),
        # Lo recorre el scheduler de avisos de vencimiento.
        Index("ix_investments_status_maturity", "status", "maturity_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)

    asset_type: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(120))
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    #: ARS, USD, USDT, EUR (USDT tiene 4 letras: no entra en el String(3) del resto de finanzas).
    currency: Mapped[str] = mapped_column(String(5))

    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8), nullable=True)
    invested_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    #: Valor manual. None = se calcula (plazo fijo devengado) o vale lo invertido.
    current_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    #: % anual (30 = 30 % TNA).
    interest_rate_tna: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 4), nullable=True)

    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    maturity_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    institution: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(10), default="active", server_default="active")
    notify_maturity: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    #: Minutos al este de UTC, lo manda el cliente en cada create/update (mismo
    #: patron que `Reminder`). None = el scheduler usa el de Argentina.
    timezone_offset_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Punto de extension para cotizaciones automaticas (hoy solo "manual").
    price_source: Mapped[str] = mapped_column(String(20), default="manual", server_default="manual")
    last_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8), nullable=True)
    last_price_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    value_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    #: Vencimiento para el que ya se mando el aviso "vence mañana" / "vence hoy".
    #: Se guarda la fecha (no un booleano) para que cambiar el vencimiento
    #: rehabilite los avisos sin resetear nada.
    eve_notice_for: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    day_notice_for: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

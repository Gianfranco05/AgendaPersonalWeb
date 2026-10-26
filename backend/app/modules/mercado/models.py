"""Datos de mercado compartidos por todos los usuarios.

Son tablas GLOBALES (sin `user_id`): una cotizacion del dolar no pertenece a
nadie. Por eso no van en `OWNED_TABLES` (export/borrado de cuenta) y ningun
dato del usuario viaja nunca a las APIs externas.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class FxQuote(Base):
    """Ultima cotizacion del dia de un tipo de cambio (el historico diario es
    el cierre de cada dia: una fila por `(currency, kind, quote_date)`)."""

    __tablename__ = "fx_quotes"
    __table_args__ = (
        UniqueConstraint("currency", "kind", "quote_date", name="uq_fx_quotes_day"),
        Index("ix_fx_quotes_latest", "currency", "kind", "quote_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: USD | EUR
    currency: Mapped[str] = mapped_column(String(5))
    #: oficial | mep | blue | ccl | mayorista | cripto | tarjeta
    kind: Mapped[str] = mapped_column(String(20))
    #: Fecha de `source_updated_at` en hora de Argentina (UTC-3 fijo).
    quote_date: Mapped[date] = mapped_column(Date)
    buy: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    #: Es la que se usa para convertir.
    sell: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    provider: Mapped[str] = mapped_column(String(20))
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InflationMonth(Base):
    """Variacion mensual del IPC nacional (INDEC), en %."""

    __tablename__ = "inflation_monthly"

    #: Primer dia del mes.
    period: Mapped[date] = mapped_column(Date, primary_key=True)
    pct: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    provider: Mapped[str] = mapped_column(String(20))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MarketPrice(Base):
    """Cache del ultimo precio de un activo (cripto) por proveedor y moneda."""

    __tablename__ = "market_prices"
    __table_args__ = (
        UniqueConstraint("provider", "symbol", "vs_currency", name="uq_market_prices_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(20))
    symbol: Mapped[str] = mapped_column(String(20))
    #: USD | ARS | EUR
    vs_currency: Mapped[str] = mapped_column(String(5))
    price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    source_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MarketFetchState(Base):
    """Coordinacion entre workers: una fila por fuente (`fx`, `inflation`,
    `crypto`) con el proximo ciclo y el lease que toma quien consulta."""

    __tablename__ = "market_fetch_state"

    source: Mapped[str] = mapped_column(String(20), primary_key=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lease_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_success_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

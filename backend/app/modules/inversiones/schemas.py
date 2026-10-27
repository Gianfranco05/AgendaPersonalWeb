import re
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from app.config import settings
from app.modules.inversiones.valuation import FIXED_TERM, FIXED_TERM_CURRENCIES, PRICE_PROVIDERS

# Mismo tope que `Money` de finanzas (Numeric(12, 2)): un monto mas grande
# pasaba la validacion y en Postgres reventaba el INSERT con un 500.
MAX_AMOUNT = Decimal("9999999999.99")
Amount = Annotated[Decimal, Field(ge=Decimal("0"), le=MAX_AMOUNT)]
# Numeric(20, 8): 12 enteros y 8 decimales.
Quantity = Annotated[
    Decimal, Field(ge=Decimal("0"), le=Decimal("999999999999"), decimal_places=8)
]
# Numeric(7, 4): hasta 999,9999 %.
Tna = Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("999.9999"), decimal_places=4)]
TzOffset = Annotated[int, Field(ge=-840, le=840)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]

MIN_DATE = date(1970, 1, 1)
MAX_DATE = date(2100, 12, 31)
TICKER_RE = re.compile(r"^[A-Z0-9.\-]{1,20}$")

#: "manual" o cualquier proveedor registrado en PRICE_PROVIDERS (hoy "coingecko").
ALLOWED_PRICE_SOURCES = {"manual"} | set(PRICE_PROVIDERS)


class AssetType(str, Enum):
    STOCK = "stock"
    FIXED_TERM = "fixed_term"
    CRYPTO = "crypto"
    BOND = "bond"
    FUND = "fund"
    FX = "fx"
    REAL_ESTATE = "real_estate"
    VEHICLE = "vehicle"
    OTHER = "other"


class InvestmentCurrency(str, Enum):
    ARS = "ARS"
    USD = "USD"
    USDT = "USDT"
    EUR = "EUR"


class InvestmentStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"


# ── Validadores compartidos por Create y Update ─────────────────────────────


def _clean_ticker(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    ticker = value.strip().upper()
    if not ticker:
        return None
    if not TICKER_RE.match(ticker):
        raise ValueError("El ticker solo admite letras, numeros, punto y guion (hasta 20)")
    return ticker


def _check_date(value: Optional[date]) -> Optional[date]:
    if value is not None and not (MIN_DATE <= value <= MAX_DATE):
        raise ValueError("La fecha debe estar entre 1970 y 2100")
    return value


def _check_price_source(value: Optional[str]) -> Optional[str]:
    if value is not None and value not in ALLOWED_PRICE_SOURCES:
        allowed = ", ".join(f"'{k}'" for k in sorted(ALLOWED_PRICE_SOURCES))
        raise ValueError(f"Fuente de precio no soportada (solo {allowed})")
    return value


def validate_price_source_state(
    price_source: str, asset_type: str, ticker: Optional[str], quantity: Any
) -> None:
    """Un proveedor automatico exige un activo que sepa cotizar. Se valida
    sobre el estado resultante (create y update), como las reglas de plazo fijo."""
    if price_source == "manual":
        return
    provider = PRICE_PROVIDERS.get(price_source)
    if provider is None:
        raise ValueError("Fuente de precio no soportada")
    if price_source == "coingecko" and not settings.MARKET_CRYPTO_ENABLED:
        raise ValueError("La cotización automática de cripto no está disponible por ahora")
    if asset_type not in provider.supported_types:
        raise ValueError("La cotización automática solo está disponible para criptomonedas")
    if not ticker or not provider.supports(ticker):
        raise ValueError("No tenemos cotización automática para ese ticker")
    if quantity is None or quantity <= 0:
        raise ValueError("La cotización automática necesita la cantidad (mayor a 0)")


def validate_fixed_term_state(
    asset_type: str,
    currency: str,
    interest_rate_tna: Any,
    start_date: Optional[date],
    maturity_date: Optional[date],
) -> None:
    """Reglas cruzadas de fechas y de plazo fijo. Se usa en Create (sobre el
    payload) y en el service para Update (sobre el estado resultante)."""
    if start_date and maturity_date and maturity_date < start_date:
        raise ValueError("El vencimiento no puede ser anterior al inicio")
    if asset_type == FIXED_TERM:
        if start_date is None or maturity_date is None:
            raise ValueError("El plazo fijo necesita fecha de inicio y de vencimiento")
        if maturity_date <= start_date:
            raise ValueError("El vencimiento del plazo fijo debe ser posterior al inicio")
        if interest_rate_tna is None:
            raise ValueError("El plazo fijo necesita la TNA")
        if currency not in FIXED_TERM_CURRENCIES:
            raise ValueError("El plazo fijo solo puede ser en ARS o USD")


class InvestmentCreate(BaseModel):
    asset_type: AssetType
    name: Name
    ticker: Optional[str] = None
    currency: InvestmentCurrency
    quantity: Optional[Quantity] = None
    invested_amount: Amount
    current_value: Optional[Amount] = None
    interest_rate_tna: Optional[Tna] = None
    start_date: Optional[date] = None
    maturity_date: Optional[date] = None
    institution: Optional[str] = Field(default=None, max_length=120)
    notes: Optional[str] = Field(default=None, max_length=2000)
    notify_maturity: bool = True
    timezone_offset_minutes: Optional[TzOffset] = None
    price_source: str = "manual"

    @field_validator("ticker")
    @classmethod
    def _ticker(cls, v):
        return _clean_ticker(v)

    @field_validator("start_date", "maturity_date")
    @classmethod
    def _dates(cls, v):
        return _check_date(v)

    @field_validator("price_source")
    @classmethod
    def _price_source(cls, v):
        return _check_price_source(v)

    @model_validator(mode="after")
    def _cross_field(self):
        validate_fixed_term_state(
            self.asset_type.value,
            self.currency.value,
            self.interest_rate_tna,
            self.start_date,
            self.maturity_date,
        )
        validate_price_source_state(
            self.price_source, self.asset_type.value, self.ticker, self.quantity
        )
        return self


class InvestmentUpdate(BaseModel):
    """Actualizacion parcial (`exclude_unset`). Un `null` en un campo opcional
    lo borra; en un campo obligatorio se ignora (lo resuelve el service). Las
    reglas cruzadas se validan en el service sobre el estado resultante."""

    asset_type: Optional[AssetType] = None
    name: Optional[Name] = None
    ticker: Optional[str] = None
    currency: Optional[InvestmentCurrency] = None
    quantity: Optional[Quantity] = None
    invested_amount: Optional[Amount] = None
    current_value: Optional[Amount] = None
    interest_rate_tna: Optional[Tna] = None
    start_date: Optional[date] = None
    maturity_date: Optional[date] = None
    institution: Optional[str] = Field(default=None, max_length=120)
    notes: Optional[str] = Field(default=None, max_length=2000)
    notify_maturity: Optional[bool] = None
    timezone_offset_minutes: Optional[TzOffset] = None
    price_source: Optional[str] = None
    status: Optional[InvestmentStatus] = None

    @field_validator("ticker")
    @classmethod
    def _ticker(cls, v):
        return _clean_ticker(v)

    @field_validator("start_date", "maturity_date")
    @classmethod
    def _dates(cls, v):
        return _check_date(v)

    @field_validator("price_source")
    @classmethod
    def _price_source(cls, v):
        return _check_price_source(v)


# ── Salida ──────────────────────────────────────────────────────────────────


class ProjectionOut(BaseModel):
    nominal_pct: Decimal
    inflation_pct: Decimal
    real_pct: Decimal
    estimated: bool


class RealReturnOut(BaseModel):
    nominal_pct: Decimal
    inflation_pct: Decimal
    real_pct: Decimal
    estimated: bool
    estimated_months: list[str] = []
    period_start: date
    period_end: date
    #: Solo plazos fijos no vencidos.
    projected_at_maturity: Optional[ProjectionOut] = None


class PortfolioRealReturnOut(BaseModel):
    nominal_pct: Decimal
    inflation_pct: Decimal
    real_pct: Decimal
    estimated: bool
    included_count: int
    excluded_count: int


class FixedTermOut(BaseModel):
    term_days: int
    interest_total: Decimal
    amount_at_maturity: Decimal
    accrued_interest: Decimal
    tea_pct: Decimal


class InvestmentOut(BaseModel):
    id: str
    asset_type: str
    name: str
    ticker: Optional[str] = None
    currency: str
    quantity: Optional[Decimal] = None
    invested_amount: Decimal
    current_value: Optional[Decimal] = None
    interest_rate_tna: Optional[Decimal] = None
    start_date: Optional[date] = None
    maturity_date: Optional[date] = None
    institution: Optional[str] = None
    notes: Optional[str] = None
    status: str
    notify_maturity: bool
    timezone_offset_minutes: Optional[int] = None
    price_source: str
    last_price: Optional[Decimal] = None
    last_price_at: Optional[datetime] = None
    value_updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    effective_value: Decimal
    value_source: str
    gain: Decimal
    gain_pct: Optional[Decimal] = None
    days_to_maturity: Optional[int] = None
    is_matured: bool
    fixed_term: Optional[FixedTermOut] = None

    #: Renovaciones de plazo fijo: el que se renovo, el que lo renovo y si se puede renovar ya.
    renewed_from_id: Optional[str] = None
    renewed_to_id: Optional[str] = None
    can_renew: bool = False

    #: "CoinGecko" cuando la cotizacion es automatica; null en manual.
    quote_provider: Optional[str] = None
    #: `last_price_at` con mas de 1 h; null si no hay cotizacion automatica.
    quote_stale: Optional[bool] = None
    real_return: Optional["RealReturnOut"] = None
    #: currency | no_start_date | too_short | no_inflation_data | no_invested_amount
    real_return_unavailable_reason: Optional[str] = None


class CurrencyBreakdown(BaseModel):
    currency: str
    invested: Decimal
    current_value: Decimal
    gain: Decimal
    count: int


class TypeBreakdown(BaseModel):
    asset_type: str
    count: int
    #: Valor convertido a ARS; null si falta alguna cotizacion para ese tipo.
    value_ars: Optional[Decimal] = None


class UpcomingMaturity(BaseModel):
    id: str
    name: str
    asset_type: str
    currency: str
    maturity_date: date
    days_to_maturity: int
    #: Monto al vencimiento (plazo fijo) o valor actual (otros tipos).
    amount: Decimal


class InvestmentSummary(BaseModel):
    by_currency: list[CurrencyBreakdown]
    by_type: list[TypeBreakdown]
    total_ars: Optional[Decimal] = None
    total_usd: Optional[Decimal] = None
    missing_rates: list[str]
    count_active: int
    upcoming_maturities: list[UpcomingMaturity]
    #: Rendimiento real de los activos en pesos con fecha de inicio; null si no hay.
    real_return_ars: Optional[PortfolioRealReturnOut] = None


class RatesOut(BaseModel):
    usd_ars: Optional[Decimal] = None
    eur_ars: Optional[Decimal] = None
    #: `as_of` de la cotizacion USD efectiva (con manual, la fecha que cargo el usuario).
    updated_at: Optional[datetime] = None

    # Cotizacion efectiva por moneda (aditivos). `*_source` es la que pidio el
    # usuario, `*_effective_source` la que se uso (oficial | mep | blue |
    # manual | manual_fallback).
    usd_source: str = "mep"
    usd_effective_source: Optional[str] = None
    usd_buy: Optional[Decimal] = None
    usd_provider: Optional[str] = None
    usd_as_of: Optional[datetime] = None
    usd_stale: bool = False
    eur_source: str = "oficial"
    eur_effective_source: Optional[str] = None
    eur_buy: Optional[Decimal] = None
    eur_provider: Optional[str] = None
    eur_as_of: Optional[datetime] = None
    eur_stale: bool = False


class NetWorthOut(BaseModel):
    cash_balance_ars: Decimal
    cash_balance_usd: Optional[Decimal] = None
    investments: InvestmentSummary
    net_worth_ars: Optional[Decimal] = None
    net_worth_usd: Optional[Decimal] = None
    rates: RatesOut
    missing_rates: list[str]
    include_investments_in_balance: bool


# ── Renovacion de plazo fijo ────────────────────────────────────────────────


class RenewMode(str, Enum):
    PRINCIPAL_AND_INTEREST = "principal_and_interest"
    PRINCIPAL_ONLY = "principal_only"


class RenewFixedTermIn(BaseModel):
    """Renovar un plazo fijo vencido (o que vence hoy). Las reglas que dependen
    de la fecha local y de la inversion (vencimiento, inicio, interes) las
    valida el service."""

    mode: RenewMode
    interest_rate_tna: Annotated[
        Decimal, Field(gt=Decimal("0"), le=Decimal("999.9999"), decimal_places=4)
    ]
    term_days: Optional[Annotated[int, Field(ge=1, le=3650)]] = None
    maturity_date: Optional[date] = None
    start_date: Optional[date] = None
    #: Lo que el banco acredito. Por defecto, el monto al vencimiento calculado.
    amount_collected: Optional[Amount] = None
    register_interest_income: bool = False
    income_category_id: Optional[str] = None
    income_bank_account_id: Optional[str] = None
    income_payment_method: str = "transfer"
    timezone_offset_minutes: Optional[TzOffset] = None

    @field_validator("start_date", "maturity_date")
    @classmethod
    def _dates(cls, v):
        return _check_date(v)

    @field_validator("income_payment_method")
    @classmethod
    def _payment_method(cls, v):
        from app.modules.finanzas.schemas import _check_enum

        return _check_enum("payment_method", v)

    @model_validator(mode="after")
    def _term(self):
        if self.term_days is None and self.maturity_date is None:
            raise ValueError("Indicá el plazo en días o la fecha de vencimiento")
        return self


class RenewOut(BaseModel):
    closed: "InvestmentOut"
    renewed: "InvestmentOut"
    interest_transaction_id: Optional[str] = None


class RenewalTermOut(BaseModel):
    id: str
    name: str
    status: str
    start_date: Optional[date] = None
    maturity_date: Optional[date] = None
    term_days: Optional[int] = None
    invested_amount: Decimal
    interest_rate_tna: Optional[Decimal] = None
    #: Cobrado al vencer (tramos cerrados) o monto al vencimiento (tramo vigente).
    amount_at_maturity: Optional[Decimal] = None
    #: Interes cobrado (cerrados) o previsto (vigente).
    interest: Optional[Decimal] = None
    renewed_from_id: Optional[str] = None


class RenewalChainOut(BaseModel):
    items: list[RenewalTermOut]
    #: Suma de los intereses ya cobrados en los tramos cerrados.
    accumulated_interest: Decimal
    currency: str

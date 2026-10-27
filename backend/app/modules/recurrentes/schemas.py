from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from app.modules.finanzas.schemas import Money, TransactionResponse, _check_enum
from app.modules.recurrentes import rules

MIN_DATE = date(1970, 1, 1)
MAX_DATE = date(2100, 12, 31)
CURRENCIES = ("ARS", "USD")

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
TzOffset = Annotated[int, Field(ge=-840, le=840)]


def _check_date(value: Optional[date]) -> Optional[date]:
    if value is not None and not (MIN_DATE <= value <= MAX_DATE):
        raise ValueError("La fecha debe estar entre 1970 y 2100")
    return value


def _check_currency(value: Optional[str]) -> Optional[str]:
    if value is not None and value not in CURRENCIES:
        raise ValueError("La moneda debe ser ARS o USD")
    return value


class RuleFields(BaseModel):
    frequency: str
    interval_count: int = 1
    weekday: Optional[int] = None
    day_of_month: Optional[int] = None
    month_of_year: Optional[int] = None

    def rule(self) -> rules.Rule:
        return rules.Rule(
            self.frequency,
            self.interval_count,
            self.weekday,
            self.day_of_month,
            self.month_of_year,
        )


class RecurringCreate(RuleFields):
    type: str
    name: Name
    description: Optional[str] = Field(default=None, max_length=1000)
    notes: Optional[str] = Field(default=None, max_length=2000)
    amount: Optional[Money] = None
    currency: str = "ARS"
    category_id: Optional[str] = None
    bank_account_id: Optional[str] = None
    account_type: str = "cash"
    payment_method: str = "cash"
    merchant_name: str = Field(default="", max_length=255)
    merchant_category: str = "other"
    start_date: date
    end_date: Optional[date] = None
    requires_confirmation: bool = False
    notify: bool = True
    generate_past: bool = False
    timezone_offset_minutes: Optional[TzOffset] = None

    @field_validator("type", "account_type", "payment_method", "merchant_category")
    @classmethod
    def _enums(cls, v, info):
        return _check_enum(info.field_name, v)

    @field_validator("currency")
    @classmethod
    def _currency(cls, v):
        return _check_currency(v)

    @field_validator("start_date", "end_date")
    @classmethod
    def _dates(cls, v):
        return _check_date(v)

    @model_validator(mode="after")
    def _cross_field(self):
        if self.type not in ("income", "expense"):
            raise ValueError("El tipo debe ser ingreso o gasto")
        if self.amount is None:
            if not self.requires_confirmation:
                raise ValueError("Ingresá el monto o activá «Confirmar el monto antes de registrar»")
        elif self.amount <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("La fecha de fin no puede ser anterior a la de inicio")
        rules.validate_rule(self.rule())
        return self


class RecurringUpdate(BaseModel):
    """Actualizacion parcial (`exclude_unset`). Un `null` en un campo opcional
    lo borra; en uno obligatorio se ignora. Las reglas cruzadas se validan en el
    service sobre el estado resultante."""

    type: Optional[str] = None
    name: Optional[Name] = None
    description: Optional[str] = Field(default=None, max_length=1000)
    notes: Optional[str] = Field(default=None, max_length=2000)
    amount: Optional[Money] = None
    currency: Optional[str] = None
    category_id: Optional[str] = None
    bank_account_id: Optional[str] = None
    account_type: Optional[str] = None
    payment_method: Optional[str] = None
    merchant_name: Optional[str] = Field(default=None, max_length=255)
    merchant_category: Optional[str] = None
    frequency: Optional[str] = None
    interval_count: Optional[int] = None
    weekday: Optional[int] = None
    day_of_month: Optional[int] = None
    month_of_year: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    requires_confirmation: Optional[bool] = None
    notify: Optional[bool] = None
    timezone_offset_minutes: Optional[TzOffset] = None

    @field_validator("type", "account_type", "payment_method", "merchant_category")
    @classmethod
    def _enums(cls, v, info):
        return _check_enum(info.field_name, v)

    @field_validator("currency")
    @classmethod
    def _currency(cls, v):
        return _check_currency(v)

    @field_validator("start_date", "end_date")
    @classmethod
    def _dates(cls, v):
        return _check_date(v)


class TzBody(BaseModel):
    timezone_offset_minutes: Optional[TzOffset] = None


class PreviewIn(RuleFields):
    start_date: date
    end_date: Optional[date] = None
    generate_past: bool = False
    tz_offset_minutes: Optional[TzOffset] = None

    @field_validator("start_date", "end_date")
    @classmethod
    def _dates(cls, v):
        return _check_date(v)

    @model_validator(mode="after")
    def _rule(self):
        rules.validate_rule(self.rule())
        return self


class PreviewOut(BaseModel):
    anchor_date: date
    dates: list[date]


class ConfirmIn(BaseModel):
    amount: Money
    transaction_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=2000)
    timezone_offset_minutes: Optional[TzOffset] = None

    @field_validator("amount")
    @classmethod
    def _positive(cls, v):
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return v

    @field_validator("transaction_date")
    @classmethod
    def _date(cls, v):
        return _check_date(v)


# ── Salida ──────────────────────────────────────────────────────────────────


class OccurrenceOut(BaseModel):
    id: str
    recurrence_id: str
    occurrence_date: date
    status: str
    suggested_amount: Optional[Decimal] = None
    transaction_id: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    # De la plantilla, para mostrar el pendiente sin pedirla aparte.
    name: Optional[str] = None
    type: Optional[str] = None
    currency: Optional[str] = None
    transaction: Optional[TransactionResponse] = None


class RecurringOut(BaseModel):
    id: str
    type: str
    name: str
    description: Optional[str] = None
    notes: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str
    category_id: Optional[str] = None
    bank_account_id: Optional[str] = None
    account_type: str
    payment_method: str
    merchant_name: str
    merchant_category: str
    frequency: str
    interval_count: int
    weekday: Optional[int] = None
    day_of_month: Optional[int] = None
    month_of_year: Optional[int] = None
    start_date: date
    end_date: Optional[date] = None
    anchor_date: date
    next_occurrence_date: Optional[date] = None
    last_occurrence_date: Optional[date] = None
    status: str
    paused_at: Optional[datetime] = None
    requires_confirmation: bool
    notify: bool
    timezone_offset_minutes: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    state: Literal["active", "paused", "finished"]
    rule_label: str
    pending_count: int = 0
    last_amount: Optional[Decimal] = None


class RecurringDetailOut(RecurringOut):
    recent_occurrences: list[OccurrenceOut] = []
    next_dates: list[date] = []


class UpcomingItem(BaseModel):
    recurrence_id: str
    date: date
    name: str
    type: str
    amount: Optional[Decimal] = None
    currency: str
    requires_confirmation: bool


class UpcomingTotal(BaseModel):
    type: str
    currency: str
    total: Decimal


class UpcomingOut(BaseModel):
    days: int
    items: list[UpcomingItem]
    totals: list[UpcomingTotal]

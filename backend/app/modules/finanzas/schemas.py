from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID
from typing import Annotated, Optional

from pydantic import BaseModel, Field, field_validator

from app.modules.finanzas.enums import (
    AccountType,
    MerchantCategory,
    PaymentMethod,
    TransactionType,
)

# Las columnas son Numeric(12, 2) (10 enteros) e Integer (32 bits): un valor mas
# grande pasaba la validacion y en Postgres reventaba el INSERT con un 500
# (SQLite no tiene limite y lo escondia).
Money = Annotated[Decimal, Field(ge=Decimal("-9999999999.99"), le=Decimal("9999999999.99"))]
Quantity = Annotated[int, Field(ge=0, le=1_000_000_000)]

_TRANSACTION_ENUM_FIELDS = {
    "type": TransactionType,
    "account_type": AccountType,
    "payment_method": PaymentMethod,
    "merchant_category": MerchantCategory,
}


def _check_enum(field: str, value: Optional[str]) -> Optional[str]:
    enum_cls = _TRANSACTION_ENUM_FIELDS[field]
    if value is not None and value not in enum_cls._value2member_map_:
        allowed = ", ".join(enum_cls._value2member_map_)
        raise ValueError(f"{field} invalido: {value!r} (valores validos: {allowed})")
    return value


class TransactionBase(BaseModel):
    amount: Money
    currency: str = "ARS"
    type: str
    transaction_date: date
    transaction_time: Optional[time] = None
    bank_entity_name: str = ""
    account_type: str
    account_last4: str = ""
    payment_method: str
    product_name: str
    product_description: Optional[str] = None
    quantity: Optional[Quantity] = None
    unit_price: Optional[Money] = None
    merchant_name: str = ""
    merchant_category: str = "other"
    notes: Optional[str] = None
    category_id: Optional[UUID] = None


# Los enums se validan en Create/Update y no en TransactionBase a proposito:
# TransactionResponse hereda de Base, y el camino de update no validaba nada
# antes, asi que puede haber filas guardadas con valores fuera del enum
# (ej. "Efectivo" desde la web). Validarlas al serializar rompería el listado.
class TransactionCreate(TransactionBase):
    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return v

    @field_validator("type", "account_type", "payment_method", "merchant_category")
    @classmethod
    def enum_values(cls, v, info):
        return _check_enum(info.field_name, v)


class TransactionUpdate(BaseModel):
    amount: Optional[Money] = None
    currency: Optional[str] = None
    type: Optional[str] = None
    transaction_date: Optional[date] = None
    transaction_time: Optional[time] = None
    bank_entity_name: Optional[str] = None
    account_type: Optional[str] = None
    account_last4: Optional[str] = None
    payment_method: Optional[str] = None
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    quantity: Optional[Quantity] = None
    unit_price: Optional[Money] = None
    merchant_name: Optional[str] = None
    merchant_category: Optional[str] = None
    notes: Optional[str] = None
    category_id: Optional[UUID] = None

    @field_validator("type", "account_type", "payment_method", "merchant_category")
    @classmethod
    def enum_values(cls, v, info):
        return _check_enum(info.field_name, v)


class TransactionResponse(TransactionBase):
    id: UUID
    user_id: UUID
    is_recurring: bool
    recurrence_id: Optional[str] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CategoryBase(BaseModel):
    name: str
    color: str = "#6366f1"
    icon: str = "fa-folder"
    parent_id: Optional[UUID] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[UUID] = None


class CategoryResponse(CategoryBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class BankAccountBase(BaseModel):
    name: str
    bank_name: str = ""
    account_type: str
    account_number: str = ""
    last4: str = ""
    currency: str = "ARS"
    balance: Money = Decimal("0")


class BankAccountCreate(BankAccountBase):
    @field_validator("account_type")
    @classmethod
    def account_type_valid(cls, v):
        if v not in AccountType._value2member_map_:
            raise ValueError(f"Tipo de cuenta invalido: {v}")
        return v


class BankAccountUpdate(BaseModel):
    name: Optional[str] = None
    bank_name: Optional[str] = None
    account_type: Optional[str] = None
    account_number: Optional[str] = None
    last4: Optional[str] = None
    currency: Optional[str] = None
    balance: Optional[Money] = None

    @field_validator("account_type")
    @classmethod
    def account_type_valid(cls, v):
        if v is not None and v not in AccountType._value2member_map_:
            raise ValueError(f"Tipo de cuenta invalido: {v}")
        return v


class BankAccountResponse(BankAccountBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class BudgetBase(BaseModel):
    category_id: UUID
    amount: Money
    period: str = "monthly"
    alert_threshold: int = Field(default=80, ge=0, le=100)


class BudgetCreate(BudgetBase):
    pass


class BudgetResponse(BudgetBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class BudgetUpdate(BaseModel):
    category_id: Optional[UUID] = None
    amount: Optional[Money] = None
    period: Optional[str] = None
    alert_threshold: Optional[int] = Field(default=None, ge=0, le=100)


class BudgetProgress(BaseModel):
    id: UUID
    category_id: UUID
    category_name: str
    amount: Decimal
    period: str
    alert_threshold: int
    spent: Decimal
    remaining: Decimal
    percentage: float


class DashboardStats(BaseModel):
    total_income: Decimal
    total_expenses: Decimal
    balance: Decimal
    income_by_category: dict
    expenses_by_category: dict
    recent_transactions: list[TransactionResponse]

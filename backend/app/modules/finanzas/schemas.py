from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, field_validator


class TransactionBase(BaseModel):
    amount: Decimal
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
    quantity: Optional[int] = None
    unit_price: Optional[Decimal] = None
    merchant_name: str = ""
    merchant_category: str = "other"
    notes: Optional[str] = None
    category_id: Optional[UUID] = None


class TransactionCreate(TransactionBase):
    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return v


class TransactionUpdate(BaseModel):
    amount: Optional[Decimal] = None
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
    quantity: Optional[int] = None
    unit_price: Optional[Decimal] = None
    merchant_name: Optional[str] = None
    merchant_category: Optional[str] = None
    notes: Optional[str] = None
    category_id: Optional[UUID] = None


class TransactionResponse(TransactionBase):
    id: UUID
    user_id: UUID
    is_recurring: bool
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
    balance: Decimal = Decimal("0")


class BankAccountCreate(BankAccountBase):
    pass


class BankAccountResponse(BankAccountBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class BudgetBase(BaseModel):
    category_id: UUID
    amount: Decimal
    period: str = "monthly"
    alert_threshold: int = 80


class BudgetCreate(BudgetBase):
    pass


class BudgetResponse(BudgetBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class BudgetUpdate(BaseModel):
    category_id: Optional[UUID] = None
    amount: Optional[Decimal] = None
    period: Optional[str] = None
    alert_threshold: Optional[int] = None


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

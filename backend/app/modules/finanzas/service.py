from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finanzas.enums import (
    TransactionType,
    AccountType,
    PaymentMethod,
    MerchantCategory,
)
from app.modules.finanzas.models import (
    Transaction,
    Category,
    BankAccount,
)
from app.modules.finanzas.repository import (
    TransactionRepository,
    CategoryRepository,
    BankAccountRepository,
)
from app.modules.finanzas.schemas import TransactionCreate, DashboardStats


class FinanzasService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.transaction_repo = TransactionRepository(db)
        self.category_repo = CategoryRepository(db)
        self.bank_account_repo = BankAccountRepository(db)

    async def create_transaction(
        self, user_id: UUID, data: TransactionCreate
    ) -> Transaction:
        transaction = Transaction(
            user_id=user_id,
            amount=data.amount,
            currency=data.currency,
            type=TransactionType(data.type),
            transaction_date=data.transaction_date,
            transaction_time=data.transaction_time,
            bank_entity_name=data.bank_entity_name,
            account_type=AccountType(data.account_type),
            account_last4=data.account_last4,
            payment_method=PaymentMethod(data.payment_method),
            product_name=data.product_name,
            product_description=data.product_description,
            quantity=data.quantity,
            unit_price=data.unit_price,
            merchant_name=data.merchant_name,
            merchant_category=MerchantCategory(data.merchant_category),
            notes=data.notes,
            category_id=data.category_id,
        )
        return await self.transaction_repo.create(transaction)

    async def get_transactions(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        transaction_type: Optional[str] = None,
        category_id: Optional[UUID] = None,
    ):
        return await self.transaction_repo.get_all(
            user_id, skip, limit, date_from, date_to, transaction_type, category_id
        )

    async def get_transactions_paginated(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        transaction_type: Optional[str] = None,
        category_id: Optional[UUID] = None,
    ) -> tuple:
        items = await self.transaction_repo.get_all(
            user_id, skip, limit, date_from, date_to, transaction_type, category_id
        )
        total = await self.transaction_repo.count(
            user_id, date_from, date_to, transaction_type, category_id
        )
        return items, total

    async def get_transaction(self, transaction_id: UUID, user_id: UUID):
        return await self.transaction_repo.get_by_id(transaction_id, user_id)

    async def update_transaction(self, transaction: Transaction, data: dict):
        for key, value in data.items():
            if value is not None and hasattr(transaction, key):
                setattr(transaction, key, value)
        return await self.transaction_repo.update(transaction)

    async def delete_transaction(self, transaction: Transaction):
        await self.transaction_repo.delete(transaction)

    async def get_dashboard_stats(self, user_id: UUID) -> DashboardStats:
        balance = await self.transaction_repo.get_balance(user_id)
        by_category = await self.transaction_repo.get_by_category(user_id)
        recent = await self.transaction_repo.get_all(user_id, limit=10)

        categories_result = await self.category_repo.get_all(user_id)
        categories = {str(c.id): c for c in categories_result}

        income_by_cat = {}
        expenses_by_cat = {}

        for cat_id, amounts in by_category.items():
            cat_name = categories.get(cat_id, None)
            name = cat_name.name if cat_name else cat_id
            if amounts.get("income", Decimal("0")) > 0:
                income_by_cat[name] = amounts["income"]
            if amounts.get("expense", Decimal("0")) > 0:
                expenses_by_cat[name] = amounts["expense"]

        return DashboardStats(
            total_income=balance["total_income"],
            total_expenses=balance["total_expenses"],
            balance=balance["balance"],
            income_by_category=income_by_cat,
            expenses_by_category=expenses_by_cat,
            recent_transactions=recent,
        )

    async def get_categories(self, user_id: UUID):
        return await self.category_repo.get_all(user_id)

    async def create_category(
        self, user_id: UUID, name: str, color: str = "#6366f1", icon: str = "fa-folder"
    ) -> Category:
        category = Category(
            user_id=user_id,
            name=name,
            color=color,
            icon=icon,
        )
        return await self.category_repo.create(category)

    async def get_bank_accounts(self, user_id: UUID):
        return await self.bank_account_repo.get_all(user_id)

    async def create_bank_account(
        self,
        user_id: UUID,
        name: str,
        bank_name: str,
        account_type: str,
        account_number: str,
        currency: str,
    ) -> BankAccount:
        account = BankAccount(
            user_id=user_id,
            name=name,
            bank_name=bank_name,
            account_type=AccountType(account_type),
            account_number=account_number,
            last4=account_number[-4:] if len(account_number) >= 4 else account_number,
            currency=currency,
        )
        return await self.bank_account_repo.create(account)

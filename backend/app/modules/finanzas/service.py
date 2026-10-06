import calendar
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from typing import Optional

from fastapi import HTTPException
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
    Budget,
)
from app.modules.finanzas.repository import (
    TransactionRepository,
    CategoryRepository,
    BankAccountRepository,
    BudgetRepository,
)
from app.modules.finanzas.schemas import (
    TransactionCreate,
    DashboardStats,
    BudgetCreate,
    BudgetProgress,
    CategoryCreate,
    BankAccountCreate,
)


_NULLABLE_TRANSACTION_FIELDS = {
    "category_id",
    "notes",
    "transaction_time",
    "product_description",
    "quantity",
    "unit_price",
}


class FinanzasService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.transaction_repo = TransactionRepository(db)
        self.category_repo = CategoryRepository(db)
        self.bank_account_repo = BankAccountRepository(db)
        self.budget_repo = BudgetRepository(db)

    async def _ensure_own_category(self, user_id: UUID, category_id) -> None:
        """404 si la categoria no existe o es de otro usuario.

        category_id llega del cliente: sin validarlo, una transaccion o un
        presupuesto podia apuntar a la categoria de otra persona (y los
        reportes, que joinean por category_id, le mostraban su nombre), o a una
        inexistente, lo que en Postgres rompe la FK con un 500.
        """
        if category_id is None:
            return
        if await self.category_repo.get_by_id(str(category_id), str(user_id)) is None:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

    async def create_transaction(
        self, user_id: UUID, data: TransactionCreate
    ) -> Transaction:
        await self._ensure_own_category(user_id, data.category_id)
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
            category_id=str(data.category_id) if data.category_id else None,
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
        await self._ensure_own_category(transaction.user_id, data.get("category_id"))
        # `data` viene con exclude_unset, asi que un None es un null mandado a
        # proposito ("quitar la categoria"), no un campo omitido. Se respeta
        # solo en columnas que aceptan vacio; en el resto (amount, type...)
        # un null romperia el NOT NULL, asi que se ignora como antes.
        for key, value in data.items():
            if not hasattr(transaction, key):
                continue
            if value is None and key not in _NULLABLE_TRANSACTION_FIELDS:
                continue
            if key == "category_id" and value is not None:
                value = str(value)
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

    async def get_category(self, category_id: UUID, user_id: UUID):
        return await self.category_repo.get_by_id(category_id, user_id)

    async def create_category(self, user_id: UUID, data: CategoryCreate) -> Category:
        await self._ensure_own_category(user_id, data.parent_id)
        category = Category(
            user_id=user_id,
            name=data.name,
            color=data.color,
            icon=data.icon,
            parent_id=str(data.parent_id) if data.parent_id else None,
        )
        return await self.category_repo.create(category)

    async def update_category(self, category: Category, data: dict) -> Category:
        await self._ensure_own_category(category.user_id, data.get("parent_id"))
        for key, value in data.items():
            if key == "parent_id" and value is not None:
                value = str(value)
            setattr(category, key, value)
        return await self.category_repo.update(category)

    async def delete_category(self, category: Category) -> None:
        await self.category_repo.delete(category)

    async def get_bank_accounts(self, user_id: UUID):
        return await self.bank_account_repo.get_all(str(user_id))

    async def get_bank_account(self, account_id: UUID, user_id: UUID) -> Optional[BankAccount]:
        return await self.bank_account_repo.get_by_id(str(account_id), str(user_id))

    async def create_bank_account(self, user_id: UUID, data: BankAccountCreate) -> BankAccount:
        # AccountType(...) valida el valor recibido (422 si no es uno de los
        # tipos conocidos) antes de guardarlo; la columna en si es un String
        # plano, no un enum de base de datos.
        account_type = AccountType(data.account_type)
        last4 = data.last4 or (
            data.account_number[-4:] if len(data.account_number) >= 4 else data.account_number
        )
        account = BankAccount(
            user_id=str(user_id),
            name=data.name,
            bank_name=data.bank_name,
            account_type=account_type.value,
            account_number=data.account_number,
            last4=last4,
            currency=data.currency,
            balance=data.balance,
        )
        return await self.bank_account_repo.create(account)

    async def update_bank_account(self, account: BankAccount, data: dict) -> BankAccount:
        if "account_type" in data and data["account_type"] is not None:
            data["account_type"] = AccountType(data["account_type"]).value
        for key, value in data.items():
            setattr(account, key, value)
        return await self.bank_account_repo.update(account)

    async def delete_bank_account(self, account: BankAccount) -> None:
        await self.bank_account_repo.delete(account)

    async def get_reports(self, user_id: UUID) -> dict:
        """Desglose de gastos por categoria + tendencia de los ultimos 6
        meses — mismo calculo que tenia la ruta HTML legacy
        (`finanzas/routes.py::reportes`), portado para servir como JSON."""
        by_category = await self.transaction_repo.get_expense_breakdown_by_category(str(user_id))

        today = date.today()
        month_starts = []
        for i in range(5, -1, -1):
            month = (today.month - i - 1) % 12 + 1
            year = today.year - ((i + (12 - today.month)) // 12)
            month_starts.append(date(year, month, 1))
        monthly = await self.transaction_repo.get_monthly_totals(str(user_id), month_starts)

        return {
            "by_category": by_category,
            "monthly": monthly,
            "total_expenses": sum((row["total"] for row in by_category), Decimal("0")),
        }

    async def create_budget(self, user_id: UUID, data: BudgetCreate) -> Budget:
        await self._ensure_own_category(user_id, data.category_id)
        budget = Budget(
            user_id=user_id,
            category_id=str(data.category_id),
            amount=data.amount,
            period=data.period,
            alert_threshold=data.alert_threshold,
        )
        return await self.budget_repo.create(budget)

    async def get_budgets(self, user_id: UUID):
        return await self.budget_repo.get_all(user_id)

    async def get_budget(self, budget_id: UUID, user_id: UUID):
        return await self.budget_repo.get_by_id(budget_id, user_id)

    async def update_budget(self, budget: Budget, data: dict) -> Budget:
        await self._ensure_own_category(budget.user_id, data.get("category_id"))
        for key, value in data.items():
            if key == "category_id" and value is not None:
                value = str(value)
            setattr(budget, key, value)
        return await self.budget_repo.update(budget)

    async def delete_budget(self, budget: Budget) -> None:
        await self.budget_repo.delete(budget)

    async def get_budgets_with_progress(
        self, user_id: UUID, year: int, month: int
    ) -> list[BudgetProgress]:
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])

        budgets = await self.budget_repo.get_all(user_id)
        spent_by_category = await self.transaction_repo.get_expenses_by_category_in_range(
            user_id, start, end
        )
        categories = {str(c.id): c for c in await self.category_repo.get_all(user_id)}

        result = []
        for budget in budgets:
            spent = Decimal(str(spent_by_category.get(str(budget.category_id), 0)))
            category = categories.get(str(budget.category_id))
            percentage = float(spent / budget.amount * 100) if budget.amount else 0.0
            result.append(
                BudgetProgress(
                    id=budget.id,
                    category_id=budget.category_id,
                    category_name=category.name if category else "Sin categoría",
                    amount=budget.amount,
                    period=budget.period,
                    alert_threshold=budget.alert_threshold,
                    spent=spent,
                    remaining=budget.amount - spent,
                    percentage=percentage,
                )
            )
        return result

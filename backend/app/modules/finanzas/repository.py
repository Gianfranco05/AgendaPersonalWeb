from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finanzas.enums import (
    TransactionType,
)
from app.modules.finanzas.models import (
    Transaction,
    Category,
    BankAccount,
    Budget,
)


class TransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        transaction_type: Optional[str] = None,
        category_id: Optional[str] = None,
    ) -> Sequence[Transaction]:
        query = select(Transaction).where(
            and_(
                Transaction.user_id == user_id,
                Transaction.is_deleted == False,
            )
        )

        if date_from:
            query = query.where(Transaction.transaction_date >= date_from)
        if date_to:
            query = query.where(Transaction.transaction_date <= date_to)
        if transaction_type:
            query = query.where(Transaction.type == transaction_type)
        if category_id:
            query = query.where(Transaction.category_id == category_id)

        query = query.order_by(Transaction.transaction_date.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def count(
        self,
        user_id: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        transaction_type: Optional[str] = None,
        category_id: Optional[str] = None,
    ) -> int:
        query = select(func.count()).where(
            and_(
                Transaction.user_id == user_id,
                Transaction.is_deleted == False,
            )
        )

        if date_from:
            query = query.where(Transaction.transaction_date >= date_from)
        if date_to:
            query = query.where(Transaction.transaction_date <= date_to)
        if transaction_type:
            query = query.where(Transaction.type == transaction_type)
        if category_id:
            query = query.where(Transaction.category_id == category_id)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_by_id(
        self, transaction_id: str, user_id: str
    ) -> Optional[Transaction]:
        result = await self.db.execute(
            select(Transaction).where(
                and_(
                    Transaction.id == transaction_id,
                    Transaction.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, transaction: Transaction) -> Transaction:
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction

    async def update(self, transaction: Transaction) -> Transaction:
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction

    async def delete(self, transaction: Transaction) -> None:
        transaction.is_deleted = True
        transaction.deleted_at = datetime.utcnow()
        await self.db.commit()

    async def get_balance(self, user_id: str) -> dict:
        income_result = await self.db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.type == TransactionType.INCOME,
                    Transaction.is_deleted == False,
                )
            )
        )
        total_income = income_result.scalar() or Decimal("0")

        expense_result = await self.db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.type == TransactionType.EXPENSE,
                    Transaction.is_deleted == False,
                )
            )
        )
        total_expenses = expense_result.scalar() or Decimal("0")

        return {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "balance": total_income - total_expenses,
        }

    async def get_by_category(self, user_id: str) -> dict:
        result = await self.db.execute(
            select(
                Transaction.category_id,
                Transaction.type,
                func.sum(Transaction.amount).label("total"),
            )
            .where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.is_deleted == False,
                )
            )
            .group_by(Transaction.category_id, Transaction.type)
        )

        data = {}
        for row in result.all():
            if row.category_id:
                if str(row.category_id) not in data:
                    data[str(row.category_id)] = {
                        "income": Decimal("0"),
                        "expense": Decimal("0"),
                    }
                data[str(row.category_id)][row.type.value] = row.total

        return data


class CategoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, user_id: str) -> Sequence[Category]:
        result = await self.db.execute(
            select(Category).where(Category.user_id == user_id).order_by(Category.name)
        )
        return result.scalars().all()

    async def get_by_id(self, category_id: str, user_id: str) -> Optional[Category]:
        result = await self.db.execute(
            select(Category).where(
                and_(Category.id == category_id, Category.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, category: Category) -> Category:
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def update(self, category: Category) -> Category:
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def delete(self, category: Category) -> None:
        await self.db.delete(category)
        await self.db.commit()


class BankAccountRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, user_id: str) -> Sequence[BankAccount]:
        result = await self.db.execute(
            select(BankAccount)
            .where(BankAccount.user_id == user_id)
            .order_by(BankAccount.name)
        )
        return result.scalars().all()

    async def get_by_id(self, account_id: str, user_id: str) -> Optional[BankAccount]:
        result = await self.db.execute(
            select(BankAccount).where(
                and_(BankAccount.id == account_id, BankAccount.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, account: BankAccount) -> BankAccount:
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def update(self, account: BankAccount) -> BankAccount:
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def delete(self, account: BankAccount) -> None:
        await self.db.delete(account)
        await self.db.commit()

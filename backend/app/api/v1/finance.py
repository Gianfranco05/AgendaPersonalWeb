from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.finanzas.service import FinanzasService
from app.modules.finanzas.schemas import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    BudgetCreate,
    BudgetUpdate,
    BudgetResponse,
    BudgetProgress,
)
from app.api.v1.schemas import PaginatedResponse

router = APIRouter(prefix="/finance", tags=["finance"])


from pydantic import BaseModel


class FinanceSummary(BaseModel):
    total_income: Decimal
    total_expenses: Decimal
    balance: Decimal


class CategoryWithTotals(BaseModel):
    id: str
    name: str
    color: str
    icon: str
    total_income: Decimal
    total_expenses: Decimal


@router.get("/summary", response_model=FinanceSummary)
async def get_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FinanzasService(db)
    stats = await service.get_dashboard_stats(current_user.id)
    return FinanceSummary(
        total_income=stats.total_income,
        total_expenses=stats.total_expenses,
        balance=stats.balance,
    )


@router.get("/transactions", response_model=PaginatedResponse[TransactionResponse])
async def list_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    transaction_type: Optional[str] = None,
    category_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FinanzasService(db)
    items, total = await service.get_transactions_paginated(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
        transaction_type=transaction_type,
        category_id=category_id,
    )
    page = (skip // limit) + 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=limit,
    )


@router.post("/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FinanzasService(db)
    transaction = await service.create_transaction(current_user.id, data)
    return transaction


@router.put("/transactions/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: str,
    data: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FinanzasService(db)
    transaction = await service.get_transaction(transaction_id, current_user.id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")

    update_data = data.model_dump(exclude_unset=True)
    updated = await service.update_transaction(transaction, update_data)
    return updated


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FinanzasService(db)
    transaction = await service.get_transaction(transaction_id, current_user.id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")

    await service.delete_transaction(transaction)


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FinanzasService(db)
    categories = await service.get_categories(current_user.id)
    return categories


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FinanzasService(db)
    return await service.create_category(current_user.id, data)


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FinanzasService(db)
    category = await service.get_category(category_id, current_user.id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    update_data = data.model_dump(exclude_unset=True)
    return await service.update_category(category, update_data)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FinanzasService(db)
    category = await service.get_category(category_id, current_user.id)
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    await service.delete_category(category)


@router.get("/budgets", response_model=list[BudgetProgress])
async def list_budgets(
    year: int,
    month: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FinanzasService(db)
    return await service.get_budgets_with_progress(current_user.id, year, month)


@router.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    data: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FinanzasService(db)
    return await service.create_budget(current_user.id, data)


@router.put("/budgets/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: str,
    data: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FinanzasService(db)
    budget = await service.get_budget(budget_id, current_user.id)
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    update_data = data.model_dump(exclude_unset=True)
    return await service.update_budget(budget, update_data)


@router.delete("/budgets/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FinanzasService(db)
    budget = await service.get_budget(budget_id, current_user.id)
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    await service.delete_budget(budget)

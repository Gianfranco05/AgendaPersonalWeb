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
    CategoryResponse,
)

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


@router.get("/transactions", response_model=list[TransactionResponse])
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
    transactions = await service.get_transactions(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
        transaction_type=transaction_type,
        category_id=category_id,
    )
    return transactions


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

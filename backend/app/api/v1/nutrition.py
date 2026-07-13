from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.nutricion.service import NutricionService
from app.modules.nutricion.schemas import (
    MealCreate,
    MealUpdate,
    MealOut,
    NutritionSummary,
)

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.get("/summary", response_model=NutritionSummary)
async def get_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NutricionService(db)
    return await service.get_summary(current_user.id)


@router.get("/meals", response_model=list[MealOut])
async def list_meals(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NutricionService(db)
    return await service.list_meals(current_user.id, date_from, date_to)


@router.post("/meals", response_model=MealOut, status_code=status.HTTP_201_CREATED)
async def create_meal(
    data: MealCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NutricionService(db)
    return await service.create_meal(current_user.id, data)


@router.get("/meals/{meal_id}", response_model=MealOut)
async def get_meal(
    meal_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NutricionService(db)
    meal = await service.get_meal(current_user.id, meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail="Comida no encontrada")
    return meal


@router.put("/meals/{meal_id}", response_model=MealOut)
async def update_meal(
    meal_id: str,
    data: MealUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NutricionService(db)
    meal = await service.get_meal(current_user.id, meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail="Comida no encontrada")
    return await service.update_meal(meal, data)


@router.delete("/meals/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal(
    meal_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NutricionService(db)
    meal = await service.get_meal(current_user.id, meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail="Comida no encontrada")
    await service.delete_meal(meal)

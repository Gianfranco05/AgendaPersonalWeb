from datetime import date
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.nutricion.models import Meal


class NutricionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, meal: Meal) -> Meal:
        self.db.add(meal)
        await self.db.commit()
        await self.db.refresh(meal)
        return meal

    async def get_by_id(self, meal_id: str, user_id: str) -> Optional[Meal]:
        result = await self.db.execute(
            select(Meal).where(Meal.id == meal_id, Meal.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[Meal]:
        query = select(Meal).where(Meal.user_id == user_id)
        if date_from:
            query = query.where(Meal.meal_date >= date_from)
        if date_to:
            query = query.where(Meal.meal_date <= date_to)
        query = query.order_by(Meal.meal_date.desc(), Meal.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(self, meal: Meal) -> Meal:
        await self.db.commit()
        await self.db.refresh(meal)
        return meal

    async def delete(self, meal: Meal) -> None:
        await self.db.delete(meal)
        await self.db.commit()

    async def get_totals(
        self, user_id: str, date_from: date, date_to: date
    ) -> dict:
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(Meal.calories), 0),
                func.coalesce(func.sum(Meal.protein_g), 0),
                func.coalesce(func.sum(Meal.carbs_g), 0),
                func.coalesce(func.sum(Meal.fat_g), 0),
            ).where(
                Meal.user_id == user_id,
                Meal.meal_date >= date_from,
                Meal.meal_date <= date_to,
            )
        )
        row = result.one()
        return {
            "calories": row[0],
            "protein_g": row[1],
            "carbs_g": row[2],
            "fat_g": row[3],
        }

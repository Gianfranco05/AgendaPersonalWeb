from datetime import date, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.nutricion.models import Meal
from app.modules.nutricion.repository import NutricionRepository
from app.modules.nutricion.schemas import MealCreate, MealUpdate, NutritionSummary


class NutricionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = NutricionRepository(db)

    async def create_meal(self, user_id: str, data: MealCreate) -> Meal:
        meal = Meal(
            user_id=user_id,
            meal_date=data.meal_date,
            meal_type=data.meal_type,
            name=data.name,
            notes=data.notes,
            calories=data.calories,
            protein_g=data.protein_g,
            carbs_g=data.carbs_g,
            fat_g=data.fat_g,
        )
        return await self.repo.create(meal)

    async def list_meals(
        self,
        user_id: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[Meal]:
        return await self.repo.list_by_user(user_id, date_from, date_to)

    async def get_meal(self, user_id: str, meal_id: str) -> Meal | None:
        return await self.repo.get_by_id(meal_id, user_id)

    async def update_meal(self, meal: Meal, data: MealUpdate) -> Meal:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(meal, key, value)
        return await self.repo.update(meal)

    async def delete_meal(self, meal: Meal) -> None:
        await self.repo.delete(meal)

    async def get_summary(self, user_id: str) -> NutritionSummary:
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())

        today_totals = await self.repo.get_totals(user_id, today, today)
        week_totals = await self.repo.get_totals(user_id, start_of_week, today)

        return NutritionSummary(
            today_calories=today_totals["calories"],
            today_protein_g=today_totals["protein_g"],
            today_carbs_g=today_totals["carbs_g"],
            today_fat_g=today_totals["fat_g"],
            week_calories=week_totals["calories"],
            week_protein_g=week_totals["protein_g"],
            week_carbs_g=week_totals["carbs_g"],
            week_fat_g=week_totals["fat_g"],
        )

from datetime import date, datetime
from typing import Optional, Literal

from pydantic import BaseModel

MealType = Literal["breakfast", "lunch", "dinner", "snack"]


class MealCreate(BaseModel):
    meal_date: date
    meal_type: MealType = "breakfast"
    name: str
    notes: Optional[str] = None
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None


class MealUpdate(BaseModel):
    meal_date: Optional[date] = None
    meal_type: Optional[MealType] = None
    name: Optional[str] = None
    notes: Optional[str] = None
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None


class MealOut(BaseModel):
    id: str
    user_id: str
    meal_date: date
    meal_type: str
    name: str
    notes: Optional[str] = None
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NutritionSummary(BaseModel):
    today_calories: float
    today_protein_g: float
    today_carbs_g: float
    today_fat_g: float
    week_calories: float
    week_protein_g: float
    week_carbs_g: float
    week_fat_g: float

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    goal_type: str = "binary"
    target_value: float = 1
    unit: Optional[str] = None
    color: str = "#7C3AED"
    icon: str = "fa-bullseye"
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    goal_type: Optional[str] = None
    target_value: Optional[float] = None
    unit: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reminder_enabled: Optional[bool] = None
    reminder_hour: Optional[int] = None
    reminder_minute: Optional[int] = None


class GoalOut(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str] = None
    goal_type: str
    target_value: Optional[float] = None
    current_value: float
    unit: Optional[str] = None
    color: str
    icon: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HabitRecordCreate(BaseModel):
    record_date: date
    value: float = 1
    notes: Optional[str] = None


class GoalProgress(BaseModel):
    current_value: float
    target_value: Optional[float]
    percentage: float
    streak: int


class HabitRecordOut(BaseModel):
    id: str
    goal_id: str
    record_date: date
    value: float
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class MonthlySummaryItem(BaseModel):
    goal_id: str
    title: str
    unit: Optional[str] = None
    total: float
    average: float

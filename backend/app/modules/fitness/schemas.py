from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class ExerciseCreate(BaseModel):
    name: str
    sets: Optional[int] = None
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    order: int = 0


class ExerciseOut(BaseModel):
    id: str
    session_id: str
    name: str
    sets: Optional[int] = None
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    order: int

    model_config = {"from_attributes": True}


class WorkoutSessionCreate(BaseModel):
    title: str
    session_date: date
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    exercises: list[ExerciseCreate] = []


class WorkoutSessionUpdate(BaseModel):
    title: Optional[str] = None
    session_date: Optional[date] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    exercises: Optional[list[ExerciseCreate]] = None


class WorkoutSessionOut(BaseModel):
    id: str
    user_id: str
    title: str
    session_date: date
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    exercises: list[ExerciseOut] = []

    model_config = {"from_attributes": True}


class FitnessSummary(BaseModel):
    sessions_this_month: int
    total_exercises: int
    last_session_date: Optional[date] = None

from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, field_validator


class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    is_all_day: bool = False
    color: str = "#3b82f6"
    location: Optional[str] = None
    recurrence_rule: Optional[str] = None
    reminder_minutes: Optional[int] = None


class EventCreate(EventBase):
    @field_validator("end_datetime")
    @classmethod
    def end_after_start(cls, v, info):
        if v and "start_datetime" in info.data and v < info.data["start_datetime"]:
            raise ValueError("La fecha de fin debe ser posterior a la fecha de inicio")
        return v


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    is_all_day: Optional[bool] = None
    color: Optional[str] = None
    location: Optional[str] = None
    recurrence_rule: Optional[str] = None
    reminder_minutes: Optional[int] = None


class EventResponse(EventBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

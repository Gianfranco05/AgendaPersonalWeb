from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    area: str = "General"
    priority: str = "media"
    due_date: Optional[date] = None
    status: str = "pending"
    order: int = 0


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    area: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    order: Optional[int] = None


class TaskMove(BaseModel):
    status: str
    order: int


class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    area: str
    priority: str
    due_date: Optional[date] = None
    status: str
    order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

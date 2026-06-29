from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserPreferenceUpdate(BaseModel):
    currency: Optional[str] = None
    theme_color: Optional[str] = None
    date_format: Optional[str] = None


class UserPreferenceOut(BaseModel):
    id: str
    user_id: str
    currency: str
    theme_color: str
    date_format: str
    google_calendar_id: str
    google_connected: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

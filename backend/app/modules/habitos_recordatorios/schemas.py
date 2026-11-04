from datetime import date
from typing import Optional

from pydantic import BaseModel, field_validator

from app.modules.habitos_recordatorios import rules


class HabitReminderSettingsOut(BaseModel):
    enabled: bool
    time: str
    daily_cap: int
    streak_alerts: bool
    timezone_offset_minutes: Optional[int] = None
    #: El usuario tiene al menos un dispositivo con push registrada.
    has_push_devices: bool


class HabitReminderSettingsUpdate(BaseModel):
    """PUT parcial. Un null explicito se ignora salvo en `timezone_offset_minutes`
    (null = volver a Argentina)."""

    enabled: Optional[bool] = None
    time: Optional[str] = None
    daily_cap: Optional[int] = None
    streak_alerts: Optional[bool] = None
    timezone_offset_minutes: Optional[int] = None

    @field_validator("time")
    @classmethod
    def _valid_time(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            rules.parse_hhmm(value)
        return value

    @field_validator("daily_cap")
    @classmethod
    def _valid_cap(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and not 1 <= value <= 5:
            raise ValueError("El máximo de avisos por día debe estar entre 1 y 5")
        return value

    @field_validator("timezone_offset_minutes")
    @classmethod
    def _valid_offset(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and not -840 <= value <= 840:
            raise ValueError("El huso horario debe estar entre -840 y 840 minutos")
        return value


class OverviewHabitOut(BaseModel):
    id: str
    title: str
    icon: Optional[str] = None
    streak: int


class OverviewSlotOut(BaseModel):
    time: str
    #: upcoming | due | missed | sent | merged | nothing | capped | no_devices
    status: str
    habits: list[OverviewHabitOut]


class TodayOverviewOut(BaseModel):
    local_date: date
    enabled: bool
    pending_count: int
    slots: list[OverviewSlotOut]

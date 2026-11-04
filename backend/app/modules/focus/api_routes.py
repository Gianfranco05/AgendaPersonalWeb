from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.modules.auth.models import User
from app.modules.focus.service import FocusService

router = APIRouter(prefix="/focus", tags=["focus"])


class FocusSessionOut(BaseModel):
    id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    label: Optional[str] = None

    model_config = {"from_attributes": True}


class StartFocusRequest(BaseModel):
    label: Optional[str] = None


class FocusSummaryOut(BaseModel):
    today_seconds: int
    week_seconds: int
    active: Optional[FocusSessionOut] = None


@router.get("/summary", response_model=FocusSummaryOut)
async def get_focus_summary(
    # Minutos al este de UTC (Buenos Aires = -180). El server no conoce la zona
    # del usuario: sin esto, "hoy" cortaria a las 21:00 hora local en Argentina.
    tz_offset_minutes: int = Query(0, ge=-840, le=840),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await FocusService(db).summary(str(current_user.id), tz_offset_minutes)


@router.post("/start", response_model=FocusSessionOut)
async def start_focus_session(
    body: StartFocusRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await FocusService(db).start(str(current_user.id), body.label if body else None)


@router.post("/stop", response_model=FocusSessionOut)
async def stop_focus_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await FocusService(db).stop(str(current_user.id))


@router.get("/sessions", response_model=list[FocusSessionOut])
async def list_focus_sessions(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await FocusService(db).list_recent(str(current_user.id), limit)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_focus_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await FocusService(db).delete(str(current_user.id), session_id)

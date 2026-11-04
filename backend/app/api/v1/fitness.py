from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.fitness.service import FitnessService
from app.modules.fitness.schemas import (
    WorkoutSessionCreate,
    WorkoutSessionUpdate,
    WorkoutSessionOut,
    FitnessSummary,
)

router = APIRouter(prefix="/fitness", tags=["fitness"])


@router.get("/summary", response_model=FitnessSummary)
async def get_summary(
    # Minutos al este de UTC (Buenos Aires = -180). Opcional: sin el, "hoy" es
    # el del server (UTC) y cambia a las 21:00 en Argentina.
    tz_offset_minutes: Optional[int] = Query(None, ge=-840, le=840),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FitnessService(db)
    return await service.get_summary(current_user.id, tz_offset_minutes)


@router.get("/sessions", response_model=list[WorkoutSessionOut])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FitnessService(db)
    return await service.list_sessions(current_user.id)


@router.post(
    "/sessions", response_model=WorkoutSessionOut, status_code=status.HTTP_201_CREATED
)
async def create_session(
    data: WorkoutSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FitnessService(db)
    return await service.create_session(current_user.id, data)


@router.get("/sessions/{session_id}", response_model=WorkoutSessionOut)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FitnessService(db)
    session = await service.get_session(current_user.id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return session


@router.put("/sessions/{session_id}", response_model=WorkoutSessionOut)
async def update_session(
    session_id: str,
    data: WorkoutSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FitnessService(db)
    session = await service.get_session(current_user.id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return await service.update_session(session, data)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FitnessService(db)
    session = await service.get_session(current_user.id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    await service.delete_session(session)

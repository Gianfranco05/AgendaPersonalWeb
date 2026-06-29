from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.metas.models import Goal, HabitRecord

router = APIRouter(prefix="/goals", tags=["goals"])


class GoalResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    goal_type: str
    target_value: Optional[float]
    current_value: float
    unit: Optional[str]
    color: str
    icon: str
    start_date: Optional[date]
    end_date: Optional[date]
    is_completed: bool
    progress: float

    model_config = {"from_attributes": True}


class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    goal_type: str = "binary"
    target_value: Optional[float] = None
    unit: Optional[str] = None
    color: str = "#7C3AED"
    icon: str = "fa-bullseye"
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class HabitCheckIn(BaseModel):
    record_date: date
    value: float = 1.0
    notes: Optional[str] = None


def _calc_progress(goal: Goal) -> float:
    if goal.goal_type == "binary":
        return 100.0 if goal.is_completed else 0.0
    if goal.target_value and goal.target_value > 0:
        return min(100.0, (goal.current_value / goal.target_value) * 100)
    return 0.0


@router.get("", response_model=list[GoalResponse])
async def list_goals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Goal)
        .where(Goal.user_id == current_user.id)
        .order_by(Goal.created_at.desc())
    )
    goals = result.scalars().all()
    return [
        GoalResponse(
            id=g.id,
            title=g.title,
            description=g.description,
            goal_type=g.goal_type,
            target_value=g.target_value,
            current_value=g.current_value,
            unit=g.unit,
            color=g.color,
            icon=g.icon,
            start_date=g.start_date,
            end_date=g.end_date,
            is_completed=g.is_completed,
            progress=_calc_progress(g),
        )
        for g in goals
    ]


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    data: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    goal = Goal(
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        goal_type=data.goal_type,
        target_value=data.target_value,
        unit=data.unit,
        color=data.color,
        icon=data.icon,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)

    return GoalResponse(
        id=goal.id,
        title=goal.title,
        description=goal.description,
        goal_type=goal.goal_type,
        target_value=goal.target_value,
        current_value=goal.current_value,
        unit=goal.unit,
        color=goal.color,
        icon=goal.icon,
        start_date=goal.start_date,
        end_date=goal.end_date,
        is_completed=goal.is_completed,
        progress=_calc_progress(goal),
    )


@router.put("/{goal_id}/checkin", response_model=GoalResponse)
async def habit_checkin(
    goal_id: str,
    data: HabitCheckIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Goal).where(
            and_(Goal.id == goal_id, Goal.user_id == current_user.id)
        )
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Meta no encontrada")

    record = HabitRecord(
        user_id=current_user.id,
        goal_id=goal_id,
        record_date=data.record_date,
        value=data.value,
        notes=data.notes,
    )
    db.add(record)

    goal.current_value = (goal.current_value or 0) + data.value
    if goal.goal_type == "binary":
        goal.is_completed = True
    elif goal.target_value and goal.current_value >= goal.target_value:
        goal.is_completed = True

    await db.commit()
    await db.refresh(goal)

    return GoalResponse(
        id=goal.id,
        title=goal.title,
        description=goal.description,
        goal_type=goal.goal_type,
        target_value=goal.target_value,
        current_value=goal.current_value,
        unit=goal.unit,
        color=goal.color,
        icon=goal.icon,
        start_date=goal.start_date,
        end_date=goal.end_date,
        is_completed=goal.is_completed,
        progress=_calc_progress(goal),
    )

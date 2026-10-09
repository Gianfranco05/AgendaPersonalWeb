from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.metas.models import Goal, HabitRecord
from app.modules.metas.service import GoalsService
from app.modules.metas.schemas import GoalUpdate

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


class GoalUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    goal_type: Optional[str] = None
    target_value: Optional[float] = None
    unit: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class HabitCheckIn(BaseModel):
    record_date: date
    value: float = 1.0
    notes: Optional[str] = None


class HabitRecordResponse(BaseModel):
    id: str
    goal_id: str
    record_date: date
    value: float
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class MonthlySummaryResponse(BaseModel):
    goal_id: str
    title: str
    unit: Optional[str] = None
    total: float
    average: float


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


@router.put("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: str,
    data: GoalUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = GoalsService(db)
    goal = await service.get_goal(current_user.id, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Meta no encontrada")
    updated = await service.update_goal(
        goal, GoalUpdate(**data.model_dump(exclude_unset=True))
    )
    return GoalResponse(
        id=updated.id,
        title=updated.title,
        description=updated.description,
        goal_type=updated.goal_type,
        target_value=updated.target_value,
        current_value=updated.current_value,
        unit=updated.unit,
        color=updated.color,
        icon=updated.icon,
        start_date=updated.start_date,
        end_date=updated.end_date,
        is_completed=updated.is_completed,
        progress=_calc_progress(updated),
    )


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = GoalsService(db)
    goal = await service.get_goal(current_user.id, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Meta no encontrada")
    await service.delete_goal(goal)


@router.get("/summary/monthly", response_model=list[MonthlySummaryResponse])
async def monthly_summary(
    year: int,
    month: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = GoalsService(db)
    summary = await service.get_monthly_summary(current_user.id, year, month)
    return [MonthlySummaryResponse(**item.model_dump()) for item in summary]


@router.get("/{goal_id}/records", response_model=list[HabitRecordResponse])
async def list_habit_records(
    goal_id: str,
    year: int,
    month: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = GoalsService(db)
    goal = await service.get_goal(current_user.id, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Meta no encontrada")
    records = await service.get_month_records(goal_id, current_user.id, year, month)
    return records


@router.post("/{goal_id}/records", response_model=HabitRecordResponse, status_code=status.HTTP_201_CREATED)
async def upsert_habit_record(
    goal_id: str,
    data: HabitCheckIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = GoalsService(db)
    goal = await service.get_goal(current_user.id, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Meta no encontrada")
    record = await service.set_habit_value(
        current_user.id, goal_id, data.record_date, data.value, data.notes
    )
    return record


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

    day_records = (
        await db.execute(
            select(HabitRecord)
            .where(
                HabitRecord.goal_id == goal_id,
                HabitRecord.user_id == current_user.id,
                HabitRecord.record_date == data.record_date,
            )
            .order_by(HabitRecord.created_at.desc())
        )
    ).scalars().all()

    # El contador se mueve exactamente lo que cambian los registros del dia:
    # antes un "deshacer" borraba todos los registros pero restaba solo el
    # delta pedido, y contador y registros quedaban desparejos.
    if data.value >= 0:
        if goal.goal_type == "binary" and day_records:
            # Un habito de si/no ya marcado ese dia no suma de nuevo (doble
            # toque, reintento de la cola offline).
            delta = 0.0
        else:
            db.add(
                HabitRecord(
                    user_id=current_user.id,
                    goal_id=goal_id,
                    record_date=data.record_date,
                    value=data.value,
                    notes=data.notes,
                )
            )
            delta = data.value
    elif goal.goal_type == "binary":
        # Deshacer un habito de si/no: el dia queda sin marcar.
        delta = -sum(r.value or 0 for r in day_records)
        await db.execute(
            delete(HabitRecord).where(
                HabitRecord.goal_id == goal_id,
                HabitRecord.user_id == current_user.id,
                HabitRecord.record_date == data.record_date,
            )
        )
    else:
        # Meta de progreso: se descuenta de los registros de ese dia, del mas
        # nuevo al mas viejo, sin guardar registros negativos.
        remaining = -data.value
        for record in day_records:
            if remaining <= 0:
                break
            value = record.value or 0
            if value <= remaining:
                remaining -= value
                await db.delete(record)
            else:
                record.value = value - remaining
                remaining = 0
        delta = data.value + remaining

    # Nunca por debajo de 0, y el estado de completada se recalcula en los dos
    # sentidos: antes un reset dejaba is_completed=True para siempre.
    goal.current_value = max(0.0, (goal.current_value or 0) + delta)
    if goal.goal_type == "binary":
        goal.is_completed = goal.current_value > 0
    elif goal.target_value:
        goal.is_completed = goal.current_value >= goal.target_value

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

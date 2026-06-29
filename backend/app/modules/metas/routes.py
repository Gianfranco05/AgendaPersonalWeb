from uuid import uuid4
from datetime import date, datetime, timedelta
from app.core.security import get_user_id_from_request
from app.core.templates import templates

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.metas.models import Goal, HabitRecord

router = APIRouter(prefix="/metas", tags=["metas"])


@router.get("/")
async def lista_metas(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    goals_result = await db.execute(
        select(Goal)
        .where(Goal.user_id == get_user_id_from_request(request))
        .where(Goal.is_completed == False)
        .order_by(Goal.created_at.desc())
    )
    goals = goals_result.scalars().all()

    completed_result = await db.execute(
        select(Goal)
        .where(Goal.user_id == get_user_id_from_request(request))
        .where(Goal.is_completed == True)
        .order_by(Goal.updated_at.desc())
    )
    completed_goals = completed_result.scalars().all()

    for goal in goals:
        records_result = await db.execute(
            select(HabitRecord)
            .where(HabitRecord.goal_id == goal.id)
            .where(HabitRecord.record_date >= date.today() - timedelta(days=7))
            .order_by(HabitRecord.record_date.desc())
        )
        goal.recent_records = records_result.scalars().all()

        if goal.goal_type == "binary":
            goal.streak = calculate_streak([r.record_date for r in goal.recent_records])
        else:
            goal.total_period = sum(r.value for r in goal.recent_records)

    today = date.today()
    return templates.TemplateResponse(request, "metas/lista.html", {"active_page": "metas", "goals": goals, "completed_goals": completed_goals, "today": today, "timedelta": timedelta})


@router.get("/nueva")
async def nueva_meta(request: Request):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)
    return templates.TemplateResponse(request, "metas/formulario.html", {"active_page": "metas", "goal": None})


@router.post("/nueva")
async def crear_meta(
    request: Request,
    db: AsyncSession = Depends(get_db),
    title: str = Form(...),
    description: str = Form(""),
    goal_type: str = Form("binary"),
    target_value: str = Form("1"),
    unit: str = Form(""),
    color: str = Form("#7C3AED"),
    icon: str = Form("fa-bullseye"),
    start_date: str = Form(""),
    end_date: str = Form(""),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
        target = float(target_value) if target_value else 1

        goal = Goal(
            id=str(uuid4()),
            user_id=get_user_id_from_request(request),
            title=title,
            description=description or None,
            goal_type=goal_type,
            target_value=target,
            current_value=0,
            unit=unit or None,
            color=color,
            icon=icon,
            start_date=start,
            end_date=end,
        )
        db.add(goal)
        await db.commit()
    except Exception as e:
        await db.rollback()

    return RedirectResponse(url="/metas/", status_code=303)


@router.get("/editar/{goal_id}")
async def editar_meta_form(
    request: Request, goal_id: str, db: AsyncSession = Depends(get_db)
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Goal).where(
            Goal.id == goal_id, Goal.user_id == get_user_id_from_request(request)
        )
    )
    goal = result.scalar_one_or_none()
    if not goal:
        return RedirectResponse(url="/metas/", status_code=303)

    return templates.TemplateResponse(request, "metas/formulario.html", {"active_page": "metas", "goal": goal})


@router.post("/editar/{goal_id}")
async def editar_meta(
    request: Request,
    goal_id: str,
    db: AsyncSession = Depends(get_db),
    title: str = Form(...),
    description: str = Form(""),
    goal_type: str = Form("binary"),
    target_value: str = Form("1"),
    unit: str = Form(""),
    color: str = Form("#7C3AED"),
    icon: str = Form("fa-bullseye"),
    start_date: str = Form(""),
    end_date: str = Form(""),
    action: str = Form("save"),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Goal).where(
            Goal.id == goal_id, Goal.user_id == get_user_id_from_request(request)
        )
    )
    goal = result.scalar_one_or_none()
    if not goal:
        return RedirectResponse(url="/metas/", status_code=303)

    if action == "delete":
        await db.execute(delete(HabitRecord).where(HabitRecord.goal_id == goal_id))
        await db.delete(goal)
    else:
        goal.title = title
        goal.description = description or None
        goal.goal_type = goal_type
        goal.target_value = float(target_value) if target_value else 1
        goal.unit = unit or None
        goal.color = color
        goal.icon = icon
        goal.start_date = (
            datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        )
        goal.end_date = (
            datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
        )

    await db.commit()
    return RedirectResponse(url="/metas/", status_code=303)


@router.post("/registrar/{goal_id}")
async def registrar_habito(
    request: Request,
    goal_id: str,
    db: AsyncSession = Depends(get_db),
    value: str = Form("1"),
    notes: str = Form(""),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Goal).where(
            Goal.id == goal_id, Goal.user_id == get_user_id_from_request(request)
        )
    )
    goal = result.scalar_one_or_none()
    if not goal:
        return RedirectResponse(url="/metas/", status_code=303)

    today = date.today()
    existing = await db.execute(
        select(HabitRecord)
        .where(HabitRecord.goal_id == goal_id)
        .where(HabitRecord.record_date == today)
    )
    record = existing.scalar_one_or_none()

    if record:
        record.value = float(value)
        record.notes = notes or None
    else:
        record = HabitRecord(
            id=str(uuid4()),
            user_id=get_user_id_from_request(request),
            goal_id=goal_id,
            record_date=today,
            value=float(value),
            notes=notes or None,
        )
        db.add(record)

    goal.current_value = goal.current_value + float(value)
    if goal.goal_type == "binary" and goal.current_value >= goal.target_value:
        days_diff = (goal.end_date or (date.today() + timedelta(days=365))) - (
            goal.start_date or date.today()
        )
        if days_diff.days > 0:
            goal.is_completed = True

    await db.commit()
    return RedirectResponse(url="/metas/", status_code=303)


@router.post("/completar/{goal_id}")
async def completar_meta(
    request: Request,
    goal_id: str,
    db: AsyncSession = Depends(get_db),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Goal).where(
            Goal.id == goal_id, Goal.user_id == get_user_id_from_request(request)
        )
    )
    goal = result.scalar_one_or_none()
    if goal:
        goal.is_completed = True
        goal.current_value = goal.target_value
        await db.commit()

    return RedirectResponse(url="/metas/", status_code=303)


def calculate_streak(dates):
    if not dates:
        return 0
    unique_dates = sorted(set(dates), reverse=True)
    today = date.today()
    start = today if today in unique_dates else today - timedelta(days=1)
    streak = 0
    expected = start
    for d in unique_dates:
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif d < expected:
            break
    return streak

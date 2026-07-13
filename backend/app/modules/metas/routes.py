from datetime import date, datetime, timedelta
from typing import List

from app.core.security import get_user_id_from_request
from app.core.templates import templates

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.metas.service import GoalsService
from app.modules.metas.schemas import GoalOut, GoalCreate, GoalUpdate

router = APIRouter(prefix="/metas", tags=["metas"])


@router.get("/")
async def lista_metas(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    service = GoalsService(db)
    goals = await service.list_active_goals(user_id)
    completed_goals = await service.list_completed_goals(user_id)

    for goal in goals:
        records = await service.repo.get_recent_records(goal.id, days=7)
        goal.recent_records = records

        if goal.goal_type == "binary":
            goal.streak = calculate_streak([r.record_date for r in records])
        else:
            goal.total_period = sum(r.value for r in records)

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
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
        target = float(target_value) if target_value else 1

        data = GoalCreate(
            title=title,
            description=description or None,
            goal_type=goal_type,
            target_value=target,
            unit=unit or None,
            color=color,
            icon=icon,
            start_date=start,
            end_date=end,
        )
        service = GoalsService(db)
        await service.create_goal(user_id, data)
    except Exception:
        pass

    return RedirectResponse(url="/metas/", status_code=303)


@router.get("/editar/{goal_id}")
async def editar_meta_form(
    request: Request, goal_id: str, db: AsyncSession = Depends(get_db)
):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    service = GoalsService(db)
    goal = await service.get_goal(user_id, goal_id)
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
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    service = GoalsService(db)
    goal = await service.get_goal(user_id, goal_id)
    if not goal:
        return RedirectResponse(url="/metas/", status_code=303)

    if action == "delete":
        await service.delete_goal(goal)
    else:
        data = GoalUpdate(
            title=title,
            description=description or None,
            goal_type=goal_type,
            target_value=float(target_value) if target_value else 1,
            unit=unit or None,
            color=color,
            icon=icon,
            start_date=(
                datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
            ),
            end_date=(
                datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
            ),
        )
        await service.update_goal(goal, data)

    return RedirectResponse(url="/metas/", status_code=303)


@router.post("/registrar/{goal_id}")
async def registrar_habito(
    request: Request,
    goal_id: str,
    db: AsyncSession = Depends(get_db),
    value: str = Form("1"),
    notes: str = Form(""),
):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    service = GoalsService(db)
    goal = await service.get_goal(user_id, goal_id)
    if not goal:
        return RedirectResponse(url="/metas/", status_code=303)

    await service.checkin_habit(user_id, goal_id, float(value), notes or None)

    return RedirectResponse(url="/metas/", status_code=303)


@router.post("/completar/{goal_id}")
async def completar_meta(
    request: Request,
    goal_id: str,
    db: AsyncSession = Depends(get_db),
):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    service = GoalsService(db)
    goal = await service.get_goal(user_id, goal_id)
    if goal:
        await service.complete_goal(goal)

    return RedirectResponse(url="/metas/", status_code=303)


@router.get("/api/goals", response_model=List[GoalOut])
async def api_goals(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    service = GoalsService(db)
    goals = await service.list_active_goals(user_id)
    return goals


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

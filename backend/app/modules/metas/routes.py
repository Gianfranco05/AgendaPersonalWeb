from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_user_id_from_request
from app.modules.metas.models import Goal, HabitRecord
from app.modules.metas.service import GoalsService
from app.modules.metas.schemas import GoalCreate, GoalOut

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
        goal.recent_records = await service.repo.get_recent_records(goal.id)
        if goal.goal_type == "binary":
            goal.streak = await service.get_streak(goal.id)
        else:
            goal.total_period = sum(r.value for r in goal.recent_records)

    return HTMLResponse(content=render_metas(goals, completed_goals))


@router.get("/api/goals", response_model=list[GoalOut])
async def api_list_goals(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)
    service = GoalsService(db)
    return await service.list_active_goals(user_id)


@router.get("/nueva")
async def nueva_meta(request: Request):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)
    return HTMLResponse(content=render_form())


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
        data = GoalCreate(
            title=title,
            description=description or None,
            goal_type=goal_type,
            target_value=float(target_value) if target_value else 1,
            unit=unit or None,
            color=color,
            icon=icon,
            start_date=datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None,
            end_date=datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None,
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

    return HTMLResponse(content=render_form(goal))


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
        await service.repo.update(goal)

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


def render_metas(goals, completed_goals):
    goals_html = ""
    if not goals:
        goals_html = """
        <div class="text-center py-12 text-[#94A3B8]">
            <i class="fas fa-bullseye text-5xl mb-4 opacity-50"></i>
            <p class="text-lg font-medium">No hay metas activas</p>
            <p class="text-sm">Crea tu primera meta para comenzar</p>
        </div>
        """
    else:
        for g in goals:
            progress = min(
                100,
                (g.current_value / g.target_value * 100) if g.target_value > 0 else 0,
            )
            streak = getattr(g, "streak", 0)

            days_left = ""
            if g.end_date:
                days = (g.end_date - date.today()).days
                if days < 0:
                    days_left = (
                        f'<span class="text-red-500">Venció hace {-days} días</span>'
                    )
                elif days == 0:
                    days_left = '<span class="text-[#F59E0B]">Último día</span>'
                else:
                    days_left = f"{days} días restantes"

            week_days = ["L", "M", "X", "J", "V", "S", "D"]
            week_html = '<div class="flex gap-1 justify-center mt-2">'
            recent_dates = [getattr(g, "recent_records", [])]
            for i in range(7):
                d = date.today() - timedelta(days=6 - i)
                found = (
                    any(r.record_date == d for r in recent_dates[0])
                    if recent_dates[0]
                    else False
                )
                bg = "#22D3EE" if found else "#E2E8F0"
                week_html += f'<div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium" style="background-color: {bg}; color: {"white" if found else "#94A3B8"};">{week_days[d.weekday()]}</div>'
            week_html += "</div>"

            goals_html += f"""
            <div class="bg-white rounded-2xl p-6 card-shadow border border-gray-100">
                <div class="flex items-start gap-4 mb-4">
                    <div class="w-12 h-12 rounded-xl flex items-center justify-center" style="background-color: {g.color}20;">
                        <i class="{g.icon}" style="color: {g.color};"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                        <h3 class="font-semibold text-[#1E293B]">{g.title}</h3>
                        {f'<p class="text-sm text-[#64748B]">{g.description}</p>' if g.description else ""}
                    </div>
                    <a href="/metas/editar/{g.id}" class="text-[#94A3B8] hover:text-[#7C3AED] transition">
                        <i class="fas fa-ellipsis-v"></i>
                    </a>
                </div>

                <div class="mb-4">
                    <div class="flex justify-between text-sm mb-1">
                        <span class="text-[#64748B]">{g.current_value} / {g.target_value} {g.unit or ""}</span>
                        <span class="font-medium" style="color: {g.color};">{progress:.0f}%</span>
                    </div>
                    <div class="h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div class="h-full rounded-full transition-all" style="width: {progress}%; background-color: {g.color};"></div>
                    </div>
                </div>

                {week_html}

                <div class="flex justify-between items-center mt-4 text-sm">
                    <span class="text-[#94A3B8]">
                        <i class="fas fa-fire mr-1"></i>{streak} días seguidos
                    </span>
                    {f'<span class="text-[#64748B]">{days_left}</span>' if days_left else ""}
                </div>

                <form method="POST" action="/metas/registrar/{g.id}" class="mt-4 flex gap-2">
                    <input type="hidden" name="value" value="{1 if g.goal_type == "binary" else 0.1}">
                    <button type="submit" class="flex-1 py-2 rounded-xl font-medium text-white transition" style="background-color: {g.color};">
                        <i class="fas fa-check mr-2"></i>{"Marcar hoy" if g.goal_type == "binary" else "Sumar 0.1"}
                    </button>
                </form>
            </div>
            """

    completed_html = ""
    if completed_goals:
        completed_html = (
            '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">'
        )
        for g in completed_goals[:6]:
            completed_html += f"""
            <div class="bg-[#D1FAE5] rounded-xl p-4 border border-[#10B981]/20 opacity-75">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-lg flex items-center justify-center bg-white/50">
                        <i class="{g.icon}" style="color: {g.color};"></i>
                    </div>
                    <div class="flex-1">
                        <p class="font-medium text-[#065F46]">{g.title}</p>
                        <p class="text-xs text-[#059669]"><i class="fas fa-check-circle mr-1"></i>Completada</p>
                    </div>
                </div>
            </div>
            """
        completed_html += "</div>"

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metas y Hábitos - Vida Personal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        * {{ font-family: 'Inter', sans-serif; }}
        .btn-primary {{
            background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%);
            transition: all 0.3s ease;
        }}
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 25px -5px rgba(124, 58, 237, 0.4);
        }}
        .card-shadow {{ box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1); }}
    </style>
</head>
<body class="bg-[#F8FAFC] min-h-screen">
    <nav class="bg-[#0F172A] text-white sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 py-4">
            <div class="flex justify-between items-center">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-[#7C3AED] to-[#22D3EE] flex items-center justify-center">
                        <i class="fas fa-sparkles"></i>
                    </div>
                    <span class="text-xl font-bold tracking-tight">Vida Personal</span>
                </div>
                <div class="flex items-center gap-2">
                    <a href="/finanzas/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Dashboard</a>
                    <a href="/finanzas/transacciones" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Finanzas</a>
                    <a href="/anotaciones/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Notas</a>
                    <a href="/eventos/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Calendario</a>
                    <a href="/metas/" class="px-5 py-2.5 rounded-xl bg-[#7C3AED] text-sm font-medium">Metas</a>
                    <a href="/ajustes/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition"><i class="fas fa-cog mr-1"></i>Ajustes</a>
                    <div class="w-px h-8 bg-white/20 mx-2"></div>
                    <a href="/auth/logout" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">
                        <i class="fas fa-sign-out-alt mr-2"></i>Salir
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-6 py-10">
        <div class="flex justify-between items-center mb-8">
            <div>
                <a href="/finanzas/" class="text-[#64748B] hover:text-[#7C3AED] transition text-sm mb-2 inline-flex items-center gap-1">
                    <i class="fas fa-arrow-left"></i>Volver al Dashboard
                </a>
                <h1 class="text-3xl font-bold text-[#1E293B]">Metas y Hábitos</h1>
                <p class="text-[#64748B] mt-1">{len(goals)} meta{
        "s" if len(goals) != 1 else ""
    } activa{"s" if len(goals) != 1 else ""}</p>
            </div>
            <a href="/metas/nueva" class="btn-primary text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2">
                <i class="fas fa-plus"></i>Nueva Meta
            </a>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-10">
            {goals_html}
        </div>

        {
        f'''
        <div class="border-t border-gray-200 pt-10">
            <h2 class="text-xl font-semibold text-[#1E293B] mb-6">Completadas Recientemente</h2>
            {completed_html}
        </div>
        '''
        if completed_html
        else ""
    }
    </main>
</body>
</html>
"""


def render_form(goal=None):
    is_edit = goal is not None
    title_val = goal.title if goal else ""
    desc_val = goal.description if goal else ""
    target_val = goal.target_value if goal else 1
    unit_val = goal.unit if goal else ""
    color_val = goal.color if goal else "#7C3AED"
    icon_val = goal.icon if goal else "fa-bullseye"
    type_val = goal.goal_type if goal else "binary"
    start_val = goal.start_date.strftime("%Y-%m-%d") if goal and goal.start_date else ""
    end_val = goal.end_date.strftime("%Y-%m-%d") if goal and goal.end_date else ""

    icons = [
        ("fa-bullseye", "Objetivo"),
        ("fa-dumbbell", "Ejercicio"),
        ("fa-book", "Lectura"),
        ("fa-water", "Hidratación"),
        ("fa-bed", "Sueño"),
        ("fa-apple-whole", "Alimentación"),
        ("fa-person-walking", "Pasos"),
        ("fa-music", "Música"),
        ("fa-code", "Código"),
        ("fa-palette", "Creatividad"),
    ]

    icon_options = ""
    for i, name in icons:
        checked = "ring-2 ring-offset-2 ring-[#7C3AED]" if icon_val == i else ""
        icon_options += f'''
        <label class="cursor-pointer" title="{name}">
            <input type="radio" name="icon" value="{i}" {"checked" if icon_val == i else ""} class="sr-only peer">
            <div class="w-10 h-10 rounded-lg bg-gray-100 peer-checked:bg-[#7C3AED] peer-checked:text-white {checked} transition-all flex items-center justify-center">
                <i class="fas {i}"></i>
            </div>
        </label>
        '''

    colors = ["#7C3AED", "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#EC4899"]

    color_options = ""
    for c in colors:
        checked = "ring-2 ring-offset-2 ring-gray-400" if color_val == c else ""
        color_options += f'''
        <label class="cursor-pointer" title="{c}">
            <input type="radio" name="color" value="{c}" {"checked" if color_val == c else ""} class="sr-only peer">
            <div class="w-10 h-10 rounded-xl {checked} transition-all" style="background-color: {c};"></div>
        </label>
        '''

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{"Editar Meta" if is_edit else "Nueva Meta"} - Vida Personal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        * {{ font-family: 'Inter', sans-serif; }}
        .btn-primary {{
            background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%);
            transition: all 0.3s ease;
        }}
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 25px -5px rgba(124, 58, 237, 0.4);
        }}
        .input-focus:focus {{
            border-color: #7C3AED;
            box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
        }}
    </style>
</head>
<body class="bg-[#F8FAFC] min-h-screen">
    <nav class="bg-[#0F172A] text-white sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 py-4">
            <div class="flex justify-between items-center">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-[#7C3AED] to-[#22D3EE] flex items-center justify-center">
                        <i class="fas fa-sparkles"></i>
                    </div>
                    <span class="text-xl font-bold tracking-tight">Vida Personal</span>
                </div>
                <div class="flex items-center gap-2">
                    <a href="/finanzas/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Dashboard</a>
                    <a href="/finanzas/transacciones" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Finanzas</a>
                    <a href="/anotaciones/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Notas</a>
                    <a href="/eventos/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Calendario</a>
                    <a href="/metas/" class="px-5 py-2.5 rounded-xl bg-[#7C3AED] text-sm font-medium">Metas</a>
                    <a href="/ajustes/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition"><i class="fas fa-cog mr-1"></i>Ajustes</a>
                    <div class="w-px h-8 bg-white/20 mx-2"></div>
                    <a href="/auth/logout" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">
                        <i class="fas fa-sign-out-alt mr-2"></i>Salir
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-2xl mx-auto px-6 py-10">
        <a href="/metas/" class="text-[#64748B] hover:text-[#7C3AED] transition text-sm mb-4 inline-flex items-center gap-1">
            <i class="fas fa-arrow-left"></i>Volver a Metas
        </a>

        <div class="bg-white rounded-2xl p-8 card-shadow border border-gray-100">
            <div class="flex items-center gap-3 mb-6">
                <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-[#7C3AED] to-[#22D3EE] flex items-center justify-center">
                    <i class="fas fa-bullseye text-white"></i>
                </div>
                <h1 class="text-2xl font-bold text-[#1E293B]">{"Editar Meta" if is_edit else "Nueva Meta"}</h1>
            </div>

            <form method="POST" action="{"/metas/editar/" + goal.id if is_edit else "/metas/nueva"}" class="space-y-6">
                <input type="hidden" name="action" value="save">

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Título</label>
                    <input type="text" name="title" required value="{title_val}"
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                        placeholder="Ej: Ejercicio diario">
                </div>

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Descripción (opcional)</label>
                    <textarea name="description" rows="2"
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none resize-none"
                        placeholder="Detalles adicionales...">{desc_val}</textarea>
                </div>

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Tipo de Meta</label>
                    <div class="grid grid-cols-2 gap-3">
                        <label class="cursor-pointer">
                            <input type="radio" name="goal_type" value="binary" {"checked" if type_val == "binary" else ""} class="sr-only peer">
                            <div class="px-4 py-3 rounded-xl border-2 border-gray-200 peer-checked:border-[#7C3AED] peer-checked:bg-[#EDE9FE] transition text-center">
                                <i class="fas fa-toggle-on text-[#7C3AED] mb-1"></i>
                                <p class="text-sm font-medium text-[#1E293B]">Sí/No</p>
                                <p class="text-xs text-[#64748B]">Completar o no</p>
                            </div>
                        </label>
                        <label class="cursor-pointer">
                            <input type="radio" name="goal_type" value="progress" {"checked" if type_val == "progress" else ""} class="sr-only peer">
                            <div class="px-4 py-3 rounded-xl border-2 border-gray-200 peer-checked:border-[#22D3EE] peer-checked:bg-[#CFFAFE] transition text-center">
                                <i class="fas fa-chart-line text-[#22D3EE] mb-1"></i>
                                <p class="text-sm font-medium text-[#1E293B]">Progreso</p>
                                <p class="text-xs text-[#64748B]">Acumular valor</p>
                            </div>
                        </label>
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-6">
                    <div>
                        <label class="block text-sm font-medium text-[#374151] mb-2">Meta target</label>
                        <input type="number" name="target_value" value="{target_val}" min="1" step="0.1" required
                            class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-[#374151] mb-2">Unidad (opcional)</label>
                        <input type="text" name="unit" value="{unit_val}"
                            class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                            placeholder="kg, páginas, etc">
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-6">
                    <div>
                        <label class="block text-sm font-medium text-[#374151] mb-2">Fecha inicio</label>
                        <input type="date" name="start_date" value="{start_val}"
                            class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-[#374151] mb-2">Fecha límite</label>
                        <input type="date" name="end_date" value="{end_val}"
                            class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none">
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-3">Icono</label>
                    <div class="flex flex-wrap gap-2">
                        {icon_options}
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-3">Color</label>
                    <div class="flex gap-3">
                        {color_options}
                    </div>
                </div>

                <div class="flex gap-4 pt-4 border-t border-gray-100">
                    <button type="submit" class="btn-primary text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2">
                        <i class="fas fa-check"></i>Guardar
                    </button>
                    {'<button type="submit" name="action" value="delete" class="px-6 py-3 rounded-xl font-medium bg-red-50 text-red-600 hover:bg-red-100 transition flex items-center gap-2">' if is_edit else ""}
                    {'<i class="fas fa-trash"></i>Eliminar' if is_edit else ""}
                    {"</button>" if is_edit else ""}
                    <a href="/metas/" class="px-6 py-3 rounded-xl font-medium bg-gray-100 text-[#64748B] hover:bg-gray-200 transition ml-auto">
                        Cancelar
                    </a>
                </div>
            </form>
        </div>
    </main>
</body>
</html>
"""

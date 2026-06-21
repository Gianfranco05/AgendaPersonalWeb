import logging

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
import json

from app.core.security import get_user_id_from_request

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.finanzas.models import Transaction, Category
from app.modules.eventos.models import Event
from app.modules.anotaciones.models import Note
from app.modules.metas.models import Goal, HabitRecord

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/finanzas", tags=["finanzas"])


@router.get("/")
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    user_id = get_user_id_from_request(request)
    today = date.today()
    month_start = today.replace(day=1)

    income_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.user_id == user_id)
        .where(Transaction.type == "income")
        .where(Transaction.is_deleted == False)
    )
    total_income = float(income_result.scalar() or 0)

    expense_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.user_id == user_id)
        .where(Transaction.type == "expense")
        .where(Transaction.is_deleted == False)
    )
    total_expense = float(expense_result.scalar() or 0)

    balance = total_income - total_expense

    month_income_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.user_id == user_id)
        .where(Transaction.type == "income")
        .where(Transaction.is_deleted == False)
        .where(Transaction.transaction_date >= month_start)
    )
    month_income = float(month_income_result.scalar() or 0)

    month_expense_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.user_id == user_id)
        .where(Transaction.type == "expense")
        .where(Transaction.is_deleted == False)
        .where(Transaction.transaction_date >= month_start)
    )
    month_expense = float(month_expense_result.scalar() or 0)
    month_balance = month_income - month_expense

    transactions_result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .where(Transaction.is_deleted == False)
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        .limit(5)
    )
    recent_transactions = transactions_result.scalars().all()

    events_result = await db.execute(
        select(Event)
        .where(Event.user_id == user_id)
        .where(Event.start_datetime >= datetime.now())
        .order_by(Event.start_datetime.asc())
        .limit(5)
    )
    upcoming_events = events_result.scalars().all()

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    today_events_result = await db.execute(
        select(Event)
        .where(Event.user_id == user_id)
        .where(Event.start_datetime >= today_start)
        .where(Event.start_datetime < today_end)
        .order_by(Event.start_datetime.asc())
    )
    today_events = today_events_result.scalars().all()

    notes_result = await db.execute(
        select(Note)
        .where(Note.user_id == user_id)
        .where(Note.is_archived == False)
        .order_by(Note.updated_at.desc())
        .limit(5)
    )
    recent_notes = notes_result.scalars().all()

    notas_sin_evento_result = await db.execute(
        select(Note)
        .where(Note.user_id == user_id)
        .where(Note.is_archived == False)
        .where(Note.event_date != None)
        .order_by(Note.event_date.asc())
    )
    notas_sin_evento = notas_sin_evento_result.scalars().all()

    goals_result = await db.execute(
        select(Goal)
        .where(Goal.user_id == user_id)
        .where(Goal.is_completed == False)
        .order_by(Goal.created_at.desc())
        .limit(3)
    )
    goals = goals_result.scalars().all()

    for goal in goals:
        today_record = await db.execute(
            select(HabitRecord)
            .where(HabitRecord.goal_id == goal.id)
            .where(HabitRecord.record_date == date.today())
        )
        goal.completed_today = today_record.scalar_one_or_none() is not None

    return HTMLResponse(
        content=render_dashboard(
            balance,
            total_income,
            total_expense,
            month_income,
            month_expense,
            month_balance,
            recent_transactions,
            upcoming_events,
            today_events,
            recent_notes,
            notas_sin_evento,
            goals,
        )
    )


@router.get("/transacciones")
async def transacciones(
    request: Request,
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    per_page: int = 25,
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    user_id = get_user_id_from_request(request)
    page = max(1, page)
    per_page = max(1, min(per_page, 100))

    count_result = await db.execute(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.user_id == user_id)
        .where(Transaction.is_deleted == False)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .where(Transaction.is_deleted == False)
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    transactions = result.scalars().all()
    return HTMLResponse(content=render_transacciones(transactions, page, per_page, total))


@router.get("/transacciones/nueva")
async def nueva_transaccion(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    categories_result = await db.execute(
        select(Category)
        .where(Category.user_id == get_user_id_from_request(request))
        .order_by(Category.name)
    )
    categories = categories_result.scalars().all()
    return HTMLResponse(content=render_nueva_transaccion(categories))


@router.post("/transacciones/nueva")
async def crear_transaccion(
    request: Request,
    db: AsyncSession = Depends(get_db),
    amount: str = Form(...),
    type: str = Form(...),
    transaction_date: str = Form(...),
    product_name: str = Form(...),
    merchant_name: str = Form(""),
    payment_method: str = Form("cash"),
    notes: str = Form(""),
    category_id: str = Form(""),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    try:
        amount_val = float(amount)
        if amount_val <= 0:
            raise ValueError("Amount must be positive")
    except (ValueError, TypeError):
        await db.rollback()
        return RedirectResponse(url="/finanzas/transacciones/nueva", status_code=303)

    try:
        transaction = Transaction(
            id=str(uuid4()),
            user_id=get_user_id_from_request(request),
            amount=amount_val,
            currency="ARS",
            type=type,
            transaction_date=transaction_date,
            product_name=product_name,
            merchant_name=merchant_name,
            payment_method=payment_method,
            notes=notes,
            account_type="cash",
            account_last4="",
            bank_entity_name="",
            merchant_category="other",
            category_id=category_id or None,
        )
        db.add(transaction)
        await db.commit()
    except Exception:
        logger.exception("Error creating transaction")
        await db.rollback()

    return RedirectResponse(url="/finanzas/", status_code=303)


@router.post("/transacciones/eliminar/{transaction_id}")
async def eliminar_transaccion(
    request: Request,
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == get_user_id_from_request(request),
        )
    )
    transaction = result.scalar_one_or_none()
    if transaction:
        transaction.is_deleted = True
        await db.commit()

    return RedirectResponse(url="/finanzas/", status_code=303)


@router.get("/transacciones/editar/{transaction_id}")
async def editar_transaccion_form(
    request: Request,
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == get_user_id_from_request(request),
            Transaction.is_deleted == False,
        )
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        return RedirectResponse(url="/finanzas/transacciones", status_code=303)

    categories_result = await db.execute(
        select(Category)
        .where(Category.user_id == get_user_id_from_request(request))
        .order_by(Category.name)
    )
    categories = categories_result.scalars().all()
    return HTMLResponse(content=render_editar_transaccion(transaction, categories))


@router.post("/transacciones/editar/{transaction_id}")
async def editar_transaccion(
    request: Request,
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
    amount: str = Form(...),
    type: str = Form(...),
    transaction_date: str = Form(...),
    product_name: str = Form(...),
    merchant_name: str = Form(""),
    payment_method: str = Form("cash"),
    notes: str = Form(""),
    category_id: str = Form(""),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == get_user_id_from_request(request),
            Transaction.is_deleted == False,
        )
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        return RedirectResponse(url="/finanzas/transacciones", status_code=303)

    try:
        amount_val = float(amount)
        if amount_val <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return RedirectResponse(
            url=f"/finanzas/transacciones/editar/{transaction_id}", status_code=303
        )

    transaction.amount = amount_val
    transaction.type = type
    transaction.transaction_date = transaction_date
    transaction.product_name = product_name
    transaction.merchant_name = merchant_name
    transaction.payment_method = payment_method
    transaction.notes = notes
    transaction.category_id = category_id or None
    await db.commit()

    return RedirectResponse(url="/finanzas/transacciones", status_code=303)


@router.get("/categorias")
async def categorias(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Category)
        .where(Category.user_id == get_user_id_from_request(request))
        .order_by(Category.name)
    )
    categories = result.scalars().all()
    return HTMLResponse(content=render_categorias(categories))


@router.post("/categorias")
async def crear_categoria(
    request: Request,
    db: AsyncSession = Depends(get_db),
    name: str = Form(...),
    color: str = Form("#6366f1"),
    icon: str = Form("fa-folder"),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    category = Category(
        id=str(uuid4()),
        user_id=get_user_id_from_request(request),
        name=name,
        color=color,
        icon=icon,
    )
    db.add(category)
    await db.commit()

    return RedirectResponse(url="/finanzas/categorias", status_code=303)


@router.get("/reportes")
async def reportes(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    user_id = get_user_id_from_request(request)

    # Gastos por categoría (sin categoría → "Sin categoría")
    cat_result = await db.execute(
        select(Category.name, Category.color, func.sum(Transaction.amount))
        .join(Transaction, Transaction.category_id == Category.id, isouter=True)
        .where(Transaction.user_id == user_id)
        .where(Transaction.type == "expense")
        .where(Transaction.is_deleted == False)
        .group_by(Category.id, Category.name, Category.color)
        .order_by(func.sum(Transaction.amount).desc())
    )
    cat_rows = cat_result.all()

    # Transacciones sin categoría
    no_cat_result = await db.execute(
        select(func.sum(Transaction.amount))
        .where(Transaction.user_id == user_id)
        .where(Transaction.type == "expense")
        .where(Transaction.is_deleted == False)
        .where(Transaction.category_id == None)
    )
    no_cat_amount = float(no_cat_result.scalar() or 0)

    cat_labels = [r[0] for r in cat_rows]
    cat_colors = [r[1] for r in cat_rows]
    cat_values = [float(r[2]) for r in cat_rows]

    if no_cat_amount > 0:
        cat_labels.append("Sin categoría")
        cat_colors.append("#94A3B8")
        cat_values.append(no_cat_amount)

    # Ingresos y gastos por mes (últimos 6 meses)
    today = date.today()
    months = []
    month_labels = []
    for i in range(5, -1, -1):
        m = (today.month - i - 1) % 12 + 1
        y = today.year - ((i + (12 - today.month)) // 12)
        months.append((y, m))
        month_labels.append(
            date(y, m, 1).strftime("%b %Y")
        )

    monthly_income = []
    monthly_expense = []
    for y, m in months:
        month_start = date(y, m, 1)
        if m == 12:
            month_end = date(y + 1, 1, 1)
        else:
            month_end = date(y, m + 1, 1)

        inc = await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .where(Transaction.user_id == user_id)
            .where(Transaction.type == "income")
            .where(Transaction.is_deleted == False)
            .where(Transaction.transaction_date >= month_start)
            .where(Transaction.transaction_date < month_end)
        )
        monthly_income.append(float(inc.scalar() or 0))

        exp = await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .where(Transaction.user_id == user_id)
            .where(Transaction.type == "expense")
            .where(Transaction.is_deleted == False)
            .where(Transaction.transaction_date >= month_start)
            .where(Transaction.transaction_date < month_end)
        )
        monthly_expense.append(float(exp.scalar() or 0))

    # Tabla resumen por mes
    monthly_summary = list(zip(month_labels, monthly_income, monthly_expense))

    return HTMLResponse(
        content=render_reportes(
            cat_labels, cat_colors, cat_values,
            month_labels, monthly_income, monthly_expense,
            monthly_summary,
        )
    )


@router.get("/api/notas-sin-evento")
async def api_notas_sin_evento(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Note)
        .where(Note.user_id == get_user_id_from_request(request))
        .where(Note.is_archived == False)
        .where(Note.event_date != None)
        .order_by(Note.event_date.asc())
    )
    notes = result.scalars().all()

    return {
        "notes": [
            {
                "id": n.id,
                "title": n.title,
                "content": n.content[:100] if n.content else "",
                "event_date": n.event_date.isoformat() if n.event_date else None,
                "color": n.color,
            }
            for n in notes
        ]
    }


def render_dashboard(
    balance,
    total_income,
    total_expense,
    month_income,
    month_expense,
    month_balance,
    recent_transactions,
    upcoming_events,
    today_events,
    recent_notes,
    notas_sin_evento,
    goals=[],
):
    transactions_html = ""
    if not recent_transactions:
        transactions_html = '<tr><td colspan="4" class="px-6 py-8 text-center text-[#94A3B8]"><i class="fas fa-receipt text-2xl mb-2"></i><p>Sin transacciones</p></td></tr>'
    else:
        for t in recent_transactions:
            is_income = t.type == "income"
            amount_class = "text-green-600" if is_income else "text-red-600"
            amount_prefix = "+" if is_income else "-"
            transactions_html += f"""
            <tr class="border-b border-gray-50 hover:bg-[#F8FAFC] transition">
                <td class="px-4 py-3">
                    <div class="flex items-center gap-3">
                        <div class="w-8 h-8 rounded-lg flex items-center justify-center {"bg-green-100" if is_income else "bg-red-100"}">
                            <i class="fas fa-{"arrow-up text-green-600" if is_income else "arrow-down text-red-600"} text-xs"></i>
                        </div>
                        <div>
                            <p class="font-medium text-[#1E293B] text-sm">{t.product_name}</p>
                            <p class="text-xs text-[#94A3B8]">{t.merchant_name or "Sin comercio"}</p>
                        </div>
                    </div>
                </td>
                <td class="px-4 py-3 text-xs text-[#64748B]">{t.transaction_date}</td>
                <td class="px-4 py-3 text-sm font-semibold {amount_class}">{amount_prefix}${t.amount:,.2f}</td>
                <td class="px-4 py-3">
                    <form action="/finanzas/transacciones/eliminar/{t.id}" method="POST" onsubmit="return confirm('¿Eliminar esta transacción?');">
                        <button type="submit" class="text-[#94A3B8] hover:text-red-500 transition">
                            <i class="fas fa-trash-alt text-xs"></i>
                        </button>
                    </form>
                </td>
            </tr>
            """

    events_html = ""
    if not upcoming_events and not today_events:
        events_html = '<div class="text-center py-6 text-[#94A3B8]"><i class="fas fa-calendar text-2xl mb-2"></i><p>Sin eventos próximos</p></div>'
    else:
        for e in today_events:
            time_str = e.start_datetime.strftime("%H:%M")
            events_html += f"""
            <div class="flex items-start gap-3 p-3 rounded-xl bg-[#7C3AED]/10 border border-[#7C3AED]/20">
                <div class="w-10 h-10 rounded-lg flex items-center justify-center" style="background-color: {e.color}20;">
                    <i class="fas fa-calendar-day" style="color: {e.color};"></i>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="font-medium text-[#1E293B] text-sm">{e.title}</p>
                    <p class="text-xs text-[#7C3AED] font-medium">HOY • {time_str}</p>
                    {f'<p class="text-xs text-[#64748B] truncate">{e.location or ""}</p>' if e.location else ""}
                </div>
            </div>
            """
        for e in upcoming_events[:4]:
            date_str = e.start_datetime.strftime("%d %b")
            time_str = e.start_datetime.strftime("%H:%M")
            events_html += f"""
            <div class="flex items-start gap-3 p-3 rounded-xl bg-white border border-gray-100 hover:border-[#7C3AED]/30 transition">
                <div class="w-10 h-10 rounded-lg flex items-center justify-center" style="background-color: {e.color}20;">
                    <i class="fas fa-calendar" style="color: {e.color};"></i>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="font-medium text-[#1E293B] text-sm">{e.title}</p>
                    <p class="text-xs text-[#64748B]">{date_str} • {time_str}</p>
                    {f'<p class="text-xs text-[#94A3B8] truncate">{e.location or ""}</p>' if e.location else ""}
                </div>
            </div>
            """

    notes_html = ""
    if not recent_notes:
        notes_html = '<div class="text-center py-6 text-[#94A3B8]"><i class="fas fa-sticky-note text-2xl mb-2"></i><p>Sin notas recientes</p></div>'
    else:
        for n in recent_notes:
            notes_html += f"""
            <a href="/anotaciones/editar/{n.id}" class="flex items-start gap-3 p-3 rounded-xl hover:bg-[#F8FAFC] transition group" style="border-left: 3px solid {n.color};">
                <div class="w-8 h-8 rounded-lg flex items-center justify-center" style="background-color: {n.color}20;">
                    <i class="fas fa-sticky-note" style="color: {n.color};"></i>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="font-medium text-[#1E293B] text-sm">{n.title}</p>
                    <p class="text-xs text-[#94A3B8] line-clamp-1">{n.content[:60] if n.content else "Sin contenido"}...</p>
                </div>
                <i class="fas fa-pen text-xs text-[#94A3B8] opacity-0 group-hover:opacity-100 transition"></i>
            </a>
            """

    notas_sin_evento_html = ""
    if notas_sin_evento:
        for n in notas_sin_evento[:3]:
            date_str = n.event_date.strftime("%d %b") if n.event_date else ""
            notas_sin_evento_html += f"""
            <div class="flex items-center gap-3 p-3 rounded-xl bg-[#FEF3C7] border border-[#F59E0B]/30">
                <i class="fas fa-exclamation-circle text-[#F59E0B]"></i>
                <div class="flex-1 min-w-0">
                    <p class="font-medium text-[#1E293B] text-sm truncate">{n.title}</p>
                    <p class="text-xs text-[#F59E0B]">{date_str}</p>
                </div>
                <a href="/anotaciones/editar/{n.id}" class="text-xs text-[#7C3AED] hover:underline">Crear evento</a>
            </div>
            """

    goals_html = ""
    if goals:
        goals_html = '<div class="grid grid-cols-1 md:grid-cols-3 gap-4">'
        for g in goals:
            progress = min(
                100,
                (g.current_value / g.target_value * 100) if g.target_value > 0 else 0,
            )
            completed_class = "opacity-75" if g.completed_today else ""
            check_html = (
                '<i class="fas fa-check-circle text-green-500"></i>'
                if g.completed_today
                else ""
            )
            goals_html += f"""
            <div class="bg-white rounded-xl p-4 border border-gray-100 {completed_class}">
                <div class="flex items-center gap-3 mb-3">
                    <div class="w-10 h-10 rounded-lg flex items-center justify-center" style="background-color: {g.color}20;">
                        <i class="{g.icon}" style="color: {g.color};"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                        <p class="font-medium text-[#1E293B] text-sm truncate">{g.title}</p>
                        {check_html}
                    </div>
                </div>
                <div class="h-2 bg-gray-100 rounded-full overflow-hidden mb-2">
                    <div class="h-full rounded-full transition-all" style="width: {progress}%; background-color: {g.color};"></div>
                </div>
                <p class="text-xs text-[#64748B] text-center">{g.current_value} / {g.target_value} {g.unit or ""}</p>
            </div>
            """
        goals_html += "</div>"

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Vida Personal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        * {{ font-family: 'Inter', sans-serif; }}
        .gradient-primary {{ background: linear-gradient(135deg, #7C3AED 0%, #22D3EE 100%); }}
        .card-shadow {{ box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1); }}
        .btn-primary {{
            background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%);
            transition: all 0.3s ease;
        }}
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 25px -5px rgba(124, 58, 237, 0.4);
        }}
        .card-hover {{ transition: all 0.3s ease; }}
        .card-hover:hover {{ transform: translateY(-4px); box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); }}
        .line-clamp-1 {{ display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden; }}
    </style>
</head>
<body class="bg-[#F8FAFC] min-h-screen">
    <nav class="bg-[#0F172A] text-white sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 py-4">
            <div class="flex justify-between items-center">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
                        <i class="fas fa-sparkles"></i>
                    </div>
                    <span class="text-xl font-bold tracking-tight">Vida Personal</span>
                </div>
                <div class="flex items-center gap-2">
                    <a href="/finanzas/" class="px-5 py-2.5 rounded-xl bg-[#7C3AED] text-sm font-medium">Dashboard</a>
                    <a href="/finanzas/transacciones" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Finanzas</a>
                    <a href="/anotaciones/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Notas</a>
                    <a href="/eventos/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Calendario</a>
                    <a href="/metas/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Metas</a>
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
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-[#1E293B] mb-2">Bienvenido a tu Vida Personal</h1>
            <p class="text-[#64748B]">Organizá tus finanzas, eventos y notas en un solo lugar</p>
        </div>

        {
        "".join(
            [
                f'''<div class="mb-6 p-4 rounded-xl bg-[#FEF3C7] border border-[#F59E0B]/30">
                <div class="flex items-center gap-3 mb-3">
                    <i class="fas fa-lightbulb text-[#F59E0B]"></i>
                    <span class="font-medium text-[#1E293B]">Nota con fecha sin evento</span>
                </div>
                <div class="space-y-2">
                    {notas_sin_evento_html}
                </div>
            </div>'''
            ]
        )
        if notas_sin_evento_html
        else ""
    }

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="bg-white rounded-2xl p-6 card-shadow card-hover border border-gray-100">
                <div class="flex items-center justify-between mb-4">
                    <div class="w-12 h-12 rounded-xl bg-[#22D3EE]/10 flex items-center justify-center">
                        <i class="fas fa-wallet text-[#22D3EE] text-xl"></i>
                    </div>
                    <span class="text-xs font-medium text-[#64748B] bg-[#F1F5F9] px-3 py-1 rounded-full">Balance</span>
                </div>
                <p class="text-xs text-[#94A3B8] mb-0.5 uppercase tracking-wider">Este mes</p>
                <p class="text-3xl font-bold {"text-green-600" if month_balance >= 0 else "text-red-600"}">${month_balance:,.2f}</p>
                <p class="text-xs text-[#94A3B8] mt-2">Total histórico: <span class="font-medium text-[#64748B]">${balance:,.2f}</span></p>
            </div>

            <div class="bg-white rounded-2xl p-6 card-shadow card-hover border border-gray-100">
                <div class="flex items-center justify-between mb-4">
                    <div class="w-12 h-12 rounded-xl bg-green-100 flex items-center justify-center">
                        <i class="fas fa-arrow-trend-up text-green-500 text-xl"></i>
                    </div>
                    <span class="text-xs font-medium text-[#64748B] bg-[#F1F5F9] px-3 py-1 rounded-full">Ingresos</span>
                </div>
                <p class="text-xs text-[#94A3B8] mb-0.5 uppercase tracking-wider">Este mes</p>
                <p class="text-3xl font-bold text-green-600">+${month_income:,.2f}</p>
                <p class="text-xs text-[#94A3B8] mt-2">Total histórico: <span class="font-medium text-[#64748B]">+${total_income:,.2f}</span></p>
            </div>

            <div class="bg-white rounded-2xl p-6 card-shadow card-hover border border-gray-100">
                <div class="flex items-center justify-between mb-4">
                    <div class="w-12 h-12 rounded-xl bg-red-100 flex items-center justify-center">
                        <i class="fas fa-arrow-trend-down text-red-500 text-xl"></i>
                    </div>
                    <span class="text-xs font-medium text-[#64748B] bg-[#F1F5F9] px-3 py-1 rounded-full">Gastos</span>
                </div>
                <p class="text-xs text-[#94A3B8] mb-0.5 uppercase tracking-wider">Este mes</p>
                <p class="text-3xl font-bold text-red-600">-${month_expense:,.2f}</p>
                <p class="text-xs text-[#94A3B8] mt-2">Total histórico: <span class="font-medium text-[#64748B]">-${total_expense:,.2f}</span></p>
            </div>
        </div>

        <div class="bg-white rounded-2xl p-6 card-shadow border border-gray-100 mb-8">
            <h2 class="text-xl font-semibold text-[#1E293B] mb-6">Acciones Rápidas</h2>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <a href="/finanzas/transacciones/nueva" class="flex flex-col items-center gap-3 p-4 rounded-xl bg-[#FEF3C7] hover:bg-[#FDE68A] transition group">
                    <div class="w-12 h-12 rounded-xl bg-white flex items-center justify-center shadow-sm">
                        <i class="fas fa-receipt text-[#D97706] text-xl"></i>
                    </div>
                    <span class="text-sm font-medium text-[#92400E]">Nueva Transacción</span>
                </a>
                <a href="/eventos/nuevo" class="flex flex-col items-center gap-3 p-4 rounded-xl bg-[#DBEAFE] hover:bg-[#BFDBFE] transition group">
                    <div class="w-12 h-12 rounded-xl bg-white flex items-center justify-center shadow-sm">
                        <i class="fas fa-calendar-plus text-[#2563EB] text-xl"></i>
                    </div>
                    <span class="text-sm font-medium text-[#1E40AF]">Nuevo Evento</span>
                </a>
                <a href="/anotaciones/nueva" class="flex flex-col items-center gap-3 p-4 rounded-xl bg-[#D1FAE5] hover:bg-[#A7F3D0] transition group">
                    <div class="w-12 h-12 rounded-xl bg-white flex items-center justify-center shadow-sm">
                        <i class="fas fa-sticky-note text-[#059669] text-xl"></i>
                    </div>
                    <span class="text-sm font-medium text-[#065F46]">Nueva Nota</span>
                </a>
                <a href="/finanzas/categorias" class="flex flex-col items-center gap-3 p-4 rounded-xl bg-[#EDE9FE] hover:bg-[#DDD6FE] transition group">
                    <div class="w-12 h-12 rounded-xl bg-white flex items-center justify-center shadow-sm">
                        <i class="fas fa-tags text-[#7C3AED] text-xl"></i>
                    </div>
                    <span class="text-sm font-medium text-[#5B21B6]">Categorías</span>
                </a>
                <a href="/finanzas/reportes" class="flex flex-col items-center gap-3 p-4 rounded-xl bg-[#F0FDF4] hover:bg-[#DCFCE7] transition group">
                    <div class="w-12 h-12 rounded-xl bg-white flex items-center justify-center shadow-sm">
                        <i class="fas fa-chart-pie text-[#059669] text-xl"></i>
                    </div>
                    <span class="text-sm font-medium text-[#065F46]">Reportes</span>
                </a>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div class="bg-white rounded-2xl card-shadow border border-gray-100">
                <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center">
                    <h3 class="font-semibold text-[#1E293B]">Transacciones Recientes</h3>
                    <a href="/finanzas/transacciones" class="text-sm text-[#7C3AED] hover:underline">Ver todas</a>
                </div>
                <div class="divide-y divide-gray-50">
                    <table class="w-full">
                        <tbody>
                            {transactions_html}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="bg-white rounded-2xl card-shadow border border-gray-100">
                <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center">
                    <h3 class="font-semibold text-[#1E293B]">Eventos</h3>
                    <div class="flex gap-3">
                        <a href="/eventos/nuevo" class="text-sm text-[#7C3AED] hover:underline">+ Nuevo</a>
                        <a href="/eventos/" class="text-sm text-[#64748B] hover:text-[#7C3AED]">Ver calendario</a>
                    </div>
                </div>
                <div class="p-4 space-y-3 max-h-80 overflow-y-auto">
                    {events_html}
                </div>
            </div>
        </div>

        <div class="bg-white rounded-2xl card-shadow border border-gray-100">
            <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center">
                <h3 class="font-semibold text-[#1E293B]">Notas Recientes</h3>
                <div class="flex gap-3">
                    <a href="/anotaciones/nueva" class="text-sm text-[#7C3AED] hover:underline">+ Nueva</a>
                    <a href="/anotaciones/" class="text-sm text-[#64748B] hover:text-[#7C3AED]">Ver todas</a>
                </div>
            </div>
            <div class="p-4 divide-y divide-gray-50 max-h-64 overflow-y-auto">
                {
        notes_html
        if notes_html
        else '<div class="text-center py-6 text-[#94A3B8]"><i class="fas fa-sticky-note text-2xl mb-2"></i><p>Sin notas recientes</p></div>'
    }
            </div>
        </div>

        {
        f'''
        <div class="mt-8">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-xl font-semibold text-[#1E293B]">Metas y Hábitos</h2>
                <a href="/metas/" class="text-sm text-[#7C3AED] hover:underline">Ver todas</a>
            </div>
            {goals_html}
        </div>
        '''
        if goals_html
        else ""
    }
    </main>
</body>
</html>
"""


def render_transacciones(transactions, page=1, per_page=25, total=0):
    import math
    total_pages = max(1, math.ceil(total / per_page)) if total > 0 else 1

    rows = ""
    if not transactions:
        rows = """
        <tr>
            <td colspan="6" class="px-6 py-16 text-center">
                <div class="flex flex-col items-center text-[#94A3B8]">
                    <i class="fas fa-receipt text-5xl mb-4"></i>
                    <p class="text-lg font-medium">No hay transacciones registradas</p>
                    <p class="text-sm">Comienza agregando tu primera transacción</p>
                </div>
            </td>
        </tr>
        """
    else:
        for t in transactions:
            is_income = t.type == "income"
            amount_class = "text-green-600" if is_income else "text-red-600"
            amount_prefix = "+" if is_income else "-"
            type_badge = (
                '<span class="px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">Ingreso</span>'
                if is_income
                else '<span class="px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">Gasto</span>'
            )

            rows += f"""
            <tr class="border-b border-gray-50 hover:bg-[#F8FAFC] transition">
                <td class="px-6 py-4">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-xl {"bg-green-100" if is_income else "bg-red-100"} flex items-center justify-center">
                            <i class="fas fa-{"arrow-up text-green-600" if is_income else "arrow-down text-red-600"}"></i>
                        </div>
                        <div>
                            <p class="font-medium text-[#1E293B]">{t.product_name}</p>
                            <p class="text-sm text-[#94A3B8]">{t.merchant_name or "Sin comercio"}</p>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4">{type_badge}</td>
                <td class="px-6 py-4 text-sm text-[#64748B]">{t.transaction_date}</td>
                <td class="px-6 py-4 font-semibold {amount_class}">{amount_prefix}${t.amount:,.2f}</td>
                <td class="px-6 py-4 text-[#64748B]">{t.payment_method}</td>
                <td class="px-6 py-4">
                    <div class="flex items-center gap-2">
                        <a href="/finanzas/transacciones/editar/{t.id}" class="text-[#94A3B8] hover:text-[#7C3AED] transition p-1.5 rounded-lg hover:bg-[#EDE9FE]">
                            <i class="fas fa-pen text-xs"></i>
                        </a>
                        <form action="/finanzas/transacciones/eliminar/{t.id}" method="POST" onsubmit="return confirm('¿Eliminar esta transacción?');">
                            <button type="submit" class="text-[#94A3B8] hover:text-red-500 transition p-1.5 rounded-lg hover:bg-red-50">
                                <i class="fas fa-trash-alt text-xs"></i>
                            </button>
                        </form>
                    </div>
                </td>
            </tr>
            """

    prev_disabled = 'pointer-events-none opacity-40' if page <= 1 else ''
    next_disabled = 'pointer-events-none opacity-40' if page >= total_pages else ''
    prev_page = max(1, page - 1)
    next_page = min(total_pages, page + 1)

    pagination_html = f"""
    <div class="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
        <p class="text-sm text-[#64748B]">
            Mostrando {((page-1)*per_page)+1 if total > 0 else 0}–{min(page*per_page, total)} de <span class="font-medium">{total}</span> transacciones
        </p>
        <div class="flex items-center gap-2">
            <a href="?page={prev_page}&per_page={per_page}"
               class="px-4 py-2 rounded-xl border border-gray-200 text-sm font-medium text-[#64748B] hover:border-[#7C3AED] hover:text-[#7C3AED] transition {prev_disabled}">
                <i class="fas fa-chevron-left mr-1"></i>Anterior
            </a>
            <span class="px-4 py-2 text-sm font-medium text-[#1E293B]">
                Página {page} de {total_pages}
            </span>
            <a href="?page={next_page}&per_page={per_page}"
               class="px-4 py-2 rounded-xl border border-gray-200 text-sm font-medium text-[#64748B] hover:border-[#7C3AED] hover:text-[#7C3AED] transition {next_disabled}">
                Siguiente<i class="fas fa-chevron-right ml-1"></i>
            </a>
        </div>
    </div>
    """

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transacciones - Vida Personal</title>
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
                    <a href="/finanzas/transacciones" class="px-5 py-2.5 rounded-xl bg-[#7C3AED] text-sm font-medium">Finanzas</a>
                    <a href="/anotaciones/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Notas</a>
                    <a href="/eventos/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Calendario</a>
                    <a href="/metas/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Metas</a>
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
                <h1 class="text-3xl font-bold text-[#1E293B]">Transacciones</h1>
            </div>
            <div class="flex items-center gap-3">
                <a href="/finanzas/reportes" class="px-5 py-2.5 rounded-xl bg-white border border-gray-200 text-[#64748B] hover:border-[#7C3AED] hover:text-[#7C3AED] text-sm font-medium transition flex items-center gap-2">
                    <i class="fas fa-chart-pie"></i>Reportes
                </a>
                <a href="/finanzas/transacciones/nueva" class="btn-primary text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2">
                    <i class="fas fa-plus"></i>Nueva Transacción
                </a>
            </div>
        </div>

        <div class="bg-white rounded-2xl card-shadow border border-gray-100 overflow-hidden">
            <table class="w-full">
                <thead class="bg-[#F8FAFC] border-b border-gray-100">
                    <tr>
                        <th class="px-6 py-4 text-left text-xs font-semibold text-[#64748B] uppercase tracking-wider">Descripción</th>
                        <th class="px-6 py-4 text-left text-xs font-semibold text-[#64748B] uppercase tracking-wider">Tipo</th>
                        <th class="px-6 py-4 text-left text-xs font-semibold text-[#64748B] uppercase tracking-wider">Fecha</th>
                        <th class="px-6 py-4 text-left text-xs font-semibold text-[#64748B] uppercase tracking-wider">Monto</th>
                        <th class="px-6 py-4 text-left text-xs font-semibold text-[#64748B] uppercase tracking-wider">Método</th>
                        <th class="px-6 py-4 text-left text-xs font-semibold text-[#64748B] uppercase tracking-wider"></th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-50">
                    {rows}
                </tbody>
            </table>
            {pagination_html}
        </div>
    </main>
</body>
</html>
"""


def render_nueva_transaccion(categories):
    today = date.today().isoformat()

    category_options = ""
    if categories:
        for c in categories:
            category_options += f'<option value="{c.id}">{c.name}</option>'

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nueva Transacción - Vida Personal</title>
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
                    <a href="/finanzas/transacciones" class="px-5 py-2.5 rounded-xl bg-[#7C3AED] text-sm font-medium">Finanzas</a>
                    <a href="/anotaciones/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Notas</a>
                    <a href="/eventos/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Calendario</a>
                    <a href="/metas/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Metas</a>
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
        <a href="/finanzas/" class="text-[#64748B] hover:text-[#7C3AED] transition text-sm mb-4 inline-flex items-center gap-1">
            <i class="fas fa-arrow-left"></i>Volver al Dashboard
        </a>

        <div class="bg-white rounded-2xl p-8 card-shadow border border-gray-100">
            <h1 class="text-2xl font-bold text-[#1E293B] mb-6">Nueva Transacción</h1>

            <form method="POST" action="/finanzas/transacciones/nueva" class="space-y-6">
                <div class="grid grid-cols-2 gap-6">
                    <div>
                        <label class="block text-sm font-medium text-[#374151] mb-2">Tipo de Transacción</label>
                        <div class="grid grid-cols-2 gap-3">
                            <label class="cursor-pointer">
                                <input type="radio" name="type" value="expense" checked class="sr-only peer">
                                <div class="px-4 py-3 rounded-xl border-2 border-gray-200 peer-checked:border-red-500 peer-checked:bg-red-50 transition text-center">
                                    <i class="fas fa-arrow-down text-red-500 mb-1"></i>
                                    <p class="text-sm font-medium text-[#1E293B]">Gasto</p>
                                </div>
                            </label>
                            <label class="cursor-pointer">
                                <input type="radio" name="type" value="income" class="sr-only peer">
                                <div class="px-4 py-3 rounded-xl border-2 border-gray-200 peer-checked:border-green-500 peer-checked:bg-green-50 transition text-center">
                                    <i class="fas fa-arrow-up text-green-500 mb-1"></i>
                                    <p class="text-sm font-medium text-[#1E293B]">Ingreso</p>
                                </div>
                            </label>
                        </div>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-[#374151] mb-2">Monto (ARS)</label>
                        <div class="relative">
                            <span class="absolute left-4 top-1/2 -translate-y-1/2 text-[#64748B]">$</span>
                            <input type="number" name="amount" step="0.01" min="0.01" required
                                class="w-full pl-8 pr-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                                placeholder="0.00">
                        </div>
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Fecha</label>
                    <input type="date" name="transaction_date" required
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                        value="{today}">
                </div>

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Producto / Servicio</label>
                    <input type="text" name="product_name" required
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                        placeholder="Descripción de la transacción">
                </div>

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Comercio (opcional)</label>
                    <input type="text" name="merchant_name"
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                        placeholder="Nombre del comercio">
                </div>

                <div class="grid grid-cols-2 gap-6">
                    <div>
                        <label class="block text-sm font-medium text-[#374151] mb-2">Método de Pago</label>
                        <select name="payment_method"
                            class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none">
                            <option value="cash">Efectivo</option>
                            <option value="debit_card">Tarjeta de Débito</option>
                            <option value="credit_card">Tarjeta de Crédito</option>
                            <option value="transfer">Transferencia</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-[#374151] mb-2">Categoría (opcional)</label>
                        <select name="category_id"
                            class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none">
                            <option value="">Sin categoría</option>
                            {category_options}
                        </select>
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Notas (opcional)</label>
                    <textarea name="notes" rows="3"
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none resize-none"
                        placeholder="Agrega notas adicionales..."></textarea>
                </div>

                <div class="flex gap-4 pt-4">
                    <button type="submit" class="btn-primary text-white px-8 py-3 rounded-xl font-medium flex items-center gap-2">
                        <i class="fas fa-check"></i>Guardar Transacción
                    </button>
                    <a href="/finanzas/" class="px-8 py-3 rounded-xl font-medium bg-gray-100 text-[#64748B] hover:bg-gray-200 transition">
                        Cancelar
                    </a>
                </div>
            </form>
        </div>
    </main>
</body>
</html>
"""


def render_categorias(categories):
    cards = ""
    if not categories:
        cards = """
        <div class="text-center py-12 text-[#94A3B8]">
            <i class="fas fa-tags text-5xl mb-4 opacity-50"></i>
            <p class="text-lg font-medium">No hay categorías</p>
            <p class="text-sm">Crea tu primera categoría</p>
        </div>
        """
    else:
        for c in categories:
            cards += f"""
            <div class="bg-white rounded-xl p-4 border border-gray-100 flex items-center gap-4">
                <div class="w-10 h-10 rounded-lg flex items-center justify-center" style="background-color: {c.color}20;">
                    <i class="{c.icon}" style="color: {c.color};"></i>
                </div>
                <span class="font-medium text-[#1E293B]">{c.name}</span>
            </div>
            """

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Categorías - Vida Personal</title>
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
                    <a href="/metas/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Metas</a>
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
        <a href="/finanzas/" class="text-[#64748B] hover:text-[#7C3AED] transition text-sm mb-4 inline-flex items-center gap-1">
            <i class="fas fa-arrow-left"></i>Volver al Dashboard
        </a>
        <h1 class="text-3xl font-bold text-[#1E293B] mb-8">Categorías</h1>

        <div class="bg-white rounded-2xl p-6 card-shadow border border-gray-100 mb-8">
            <h2 class="text-lg font-semibold text-[#1E293B] mb-4">Crear Nueva Categoría</h2>
            <form method="POST" action="/finanzas/categorias" class="flex gap-4 items-end">
                <div class="flex-1">
                    <label class="block text-sm font-medium text-[#374151] mb-2">Nombre</label>
                    <input type="text" name="name" required
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                        placeholder="Nombre de la categoría">
                </div>
                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Color</label>
                    <input type="color" name="color" value="#7C3AED"
                        class="h-12 w-20 rounded-xl cursor-pointer border-2 border-gray-200">
                </div>
                <button type="submit" class="btn-primary text-white px-6 py-3 rounded-xl font-medium h-fit">
                    <i class="fas fa-plus mr-2"></i>Crear
                </button>
            </form>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {cards}
        </div>
    </main>
</body>
</html>
"""


def render_editar_transaccion(transaction, categories):
    today = transaction.transaction_date
    if hasattr(today, "isoformat"):
        today_str = today.isoformat()
    else:
        today_str = str(today)

    category_options = ""
    for c in categories:
        selected = "selected" if str(transaction.category_id) == str(c.id) else ""
        category_options += f'<option value="{c.id}" {selected}>{c.name}</option>'

    payment_methods = [
        ("cash", "Efectivo"),
        ("debit_card", "Tarjeta de Débito"),
        ("credit_card", "Tarjeta de Crédito"),
        ("transfer", "Transferencia"),
    ]
    payment_options = ""
    for val, label in payment_methods:
        selected = "selected" if transaction.payment_method == val else ""
        payment_options += f'<option value="{val}" {selected}>{label}</option>'

    expense_checked = "checked" if transaction.type == "expense" else ""
    income_checked = "checked" if transaction.type == "income" else ""

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Editar Transacción - Vida Personal</title>
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
                        <i class="fas fa-star"></i>
                    </div>
                    <span class="text-xl font-bold tracking-tight">Vida Personal</span>
                </div>
                <div class="flex items-center gap-2">
                    <a href="/finanzas/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Dashboard</a>
                    <a href="/finanzas/transacciones" class="px-5 py-2.5 rounded-xl bg-[#7C3AED] text-sm font-medium">Finanzas</a>
                    <a href="/anotaciones/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Notas</a>
                    <a href="/eventos/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Calendario</a>
                    <a href="/metas/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Metas</a>
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
        <a href="/finanzas/transacciones" class="text-[#64748B] hover:text-[#7C3AED] transition text-sm mb-4 inline-flex items-center gap-1">
            <i class="fas fa-arrow-left"></i>Volver a Transacciones
        </a>

        <div class="bg-white rounded-2xl p-8 shadow border border-gray-100">
            <h1 class="text-2xl font-bold text-[#1E293B] mb-6">Editar Transacción</h1>

            <form method="POST" action="/finanzas/transacciones/editar/{transaction.id}" class="space-y-6">
                <div class="grid grid-cols-2 gap-6">
                    <div>
                        <label class="block text-sm font-medium text-[#374151] mb-2">Tipo de Transacción</label>
                        <div class="grid grid-cols-2 gap-3">
                            <label class="cursor-pointer">
                                <input type="radio" name="type" value="expense" {expense_checked} class="sr-only peer">
                                <div class="px-4 py-3 rounded-xl border-2 border-gray-200 peer-checked:border-red-500 peer-checked:bg-red-50 transition text-center">
                                    <i class="fas fa-arrow-down text-red-500 mb-1"></i>
                                    <p class="text-sm font-medium text-[#1E293B]">Gasto</p>
                                </div>
                            </label>
                            <label class="cursor-pointer">
                                <input type="radio" name="type" value="income" {income_checked} class="sr-only peer">
                                <div class="px-4 py-3 rounded-xl border-2 border-gray-200 peer-checked:border-green-500 peer-checked:bg-green-50 transition text-center">
                                    <i class="fas fa-arrow-up text-green-500 mb-1"></i>
                                    <p class="text-sm font-medium text-[#1E293B]">Ingreso</p>
                                </div>
                            </label>
                        </div>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-[#374151] mb-2">Monto (ARS)</label>
                        <div class="relative">
                            <span class="absolute left-4 top-1/2 -translate-y-1/2 text-[#64748B]">$</span>
                            <input type="number" name="amount" step="0.01" min="0.01" required
                                value="{transaction.amount}"
                                class="w-full pl-8 pr-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none">
                        </div>
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Fecha</label>
                    <input type="date" name="transaction_date" required
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                        value="{today_str}">
                </div>

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Producto / Servicio</label>
                    <input type="text" name="product_name" required
                        value="{transaction.product_name or ''}"
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                        placeholder="Descripción de la transacción">
                </div>

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Comercio (opcional)</label>
                    <input type="text" name="merchant_name"
                        value="{transaction.merchant_name or ''}"
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                        placeholder="Nombre del comercio">
                </div>

                <div class="grid grid-cols-2 gap-6">
                    <div>
                        <label class="block text-sm font-medium text-[#374151] mb-2">Método de Pago</label>
                        <select name="payment_method"
                            class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none">
                            {payment_options}
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-[#374151] mb-2">Categoría (opcional)</label>
                        <select name="category_id"
                            class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none">
                            <option value="">Sin categoría</option>
                            {category_options}
                        </select>
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Notas (opcional)</label>
                    <textarea name="notes" rows="3"
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none resize-none"
                        placeholder="Agrega notas adicionales...">{transaction.notes or ''}</textarea>
                </div>

                <div class="flex gap-4 pt-4 border-t border-gray-100">
                    <button type="submit" class="btn-primary text-white px-8 py-3 rounded-xl font-medium flex items-center gap-2">
                        <i class="fas fa-check"></i>Guardar Cambios
                    </button>
                    <a href="/finanzas/transacciones" class="px-8 py-3 rounded-xl font-medium bg-gray-100 text-[#64748B] hover:bg-gray-200 transition">
                        Cancelar
                    </a>
                </div>
            </form>
        </div>
    </main>
</body>
</html>
"""


def render_reportes(cat_labels, cat_colors, cat_values, month_labels, monthly_income, monthly_expense, monthly_summary):
    import json as _json
    cat_labels_json = _json.dumps(cat_labels)
    cat_colors_json = _json.dumps(cat_colors)
    cat_values_json = _json.dumps(cat_values)
    month_labels_json = _json.dumps(month_labels)
    monthly_income_json = _json.dumps(monthly_income)
    monthly_expense_json = _json.dumps(monthly_expense)

    total_gastos = sum(cat_values)

    summary_rows = ""
    for label, inc, exp in monthly_summary:
        net = inc - exp
        net_class = "text-green-600 font-semibold" if net >= 0 else "text-red-600 font-semibold"
        summary_rows += f"""
        <tr class="border-b border-gray-50 hover:bg-[#F8FAFC] transition">
            <td class="px-6 py-3 text-sm text-[#1E293B] font-medium">{label}</td>
            <td class="px-6 py-3 text-sm text-green-600">+${inc:,.2f}</td>
            <td class="px-6 py-3 text-sm text-red-600">-${exp:,.2f}</td>
            <td class="px-6 py-3 text-sm {net_class}">${net:,.2f}</td>
        </tr>
        """

    cat_rows = ""
    for i, (label, val) in enumerate(zip(cat_labels, cat_values)):
        pct = (val / total_gastos * 100) if total_gastos > 0 else 0
        color = cat_colors[i] if i < len(cat_colors) else "#94A3B8"
        cat_rows += f"""
        <div class="flex items-center gap-3">
            <div class="w-3 h-3 rounded-full flex-shrink-0" style="background-color: {color};"></div>
            <div class="flex-1 min-w-0">
                <div class="flex justify-between text-sm mb-1">
                    <span class="text-[#374151] truncate">{label}</span>
                    <span class="text-[#64748B] ml-2">{pct:.1f}%</span>
                </div>
                <div class="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div class="h-full rounded-full" style="width: {pct:.1f}%; background-color: {color};"></div>
                </div>
            </div>
            <span class="text-sm font-medium text-[#1E293B] w-24 text-right">${val:,.2f}</span>
        </div>
        """

    if not cat_rows:
        cat_rows = '<p class="text-center text-[#94A3B8] py-8">Sin gastos categorizados</p>'

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reportes Financieros - Vida Personal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{ font-family: "Inter", sans-serif; }}
        .card-shadow {{ box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1); }}
    </style>
</head>
<body class="bg-[#F8FAFC] min-h-screen">
    <nav class="bg-[#0F172A] text-white sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 py-4">
            <div class="flex justify-between items-center">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-[#7C3AED] to-[#22D3EE] flex items-center justify-center">
                        <i class="fas fa-star"></i>
                    </div>
                    <span class="text-xl font-bold tracking-tight">Vida Personal</span>
                </div>
                <div class="flex items-center gap-2">
                    <a href="/finanzas/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Dashboard</a>
                    <a href="/finanzas/transacciones" class="px-5 py-2.5 rounded-xl bg-[#7C3AED] text-sm font-medium">Finanzas</a>
                    <a href="/anotaciones/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Notas</a>
                    <a href="/eventos/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Calendario</a>
                    <a href="/metas/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Metas</a>
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
        <div class="mb-8">
            <a href="/finanzas/transacciones" class="text-[#64748B] hover:text-[#7C3AED] transition text-sm mb-2 inline-flex items-center gap-1">
                <i class="fas fa-arrow-left"></i>Volver a Transacciones
            </a>
            <h1 class="text-3xl font-bold text-[#1E293B]">Reportes Financieros</h1>
            <p class="text-[#64748B] mt-1">Últimos 6 meses</p>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div class="bg-white rounded-2xl p-6 card-shadow border border-gray-100">
                <h2 class="text-lg font-semibold text-[#1E293B] mb-6">Ingresos vs Gastos</h2>
                <canvas id="barChart" height="220"></canvas>
            </div>

            <div class="bg-white rounded-2xl p-6 card-shadow border border-gray-100">
                <h2 class="text-lg font-semibold text-[#1E293B] mb-4">Gastos por Categoría</h2>
                <div class="flex items-center gap-6">
                    <div class="flex-shrink-0" style="width:180px;height:180px;">
                        <canvas id="donutChart"></canvas>
                    </div>
                    <div class="flex-1 space-y-3 overflow-y-auto max-h-48">
                        {cat_rows}
                    </div>
                </div>
            </div>
        </div>

        <div class="bg-white rounded-2xl card-shadow border border-gray-100 overflow-hidden">
            <div class="px-6 py-4 border-b border-gray-100">
                <h2 class="text-lg font-semibold text-[#1E293B]">Resumen Mensual</h2>
            </div>
            <table class="w-full">
                <thead class="bg-[#F8FAFC]">
                    <tr>
                        <th class="px-6 py-3 text-left text-xs font-semibold text-[#64748B] uppercase tracking-wider">Mes</th>
                        <th class="px-6 py-3 text-left text-xs font-semibold text-[#64748B] uppercase tracking-wider">Ingresos</th>
                        <th class="px-6 py-3 text-left text-xs font-semibold text-[#64748B] uppercase tracking-wider">Gastos</th>
                        <th class="px-6 py-3 text-left text-xs font-semibold text-[#64748B] uppercase tracking-wider">Neto</th>
                    </tr>
                </thead>
                <tbody>
                    {summary_rows}
                </tbody>
            </table>
        </div>
    </main>

    <script>
        const barCtx = document.getElementById("barChart").getContext("2d");
        new Chart(barCtx, {{
            type: "bar",
            data: {{
                labels: {month_labels_json},
                datasets: [
                    {{
                        label: "Ingresos",
                        data: {monthly_income_json},
                        backgroundColor: "rgba(34,197,94,0.8)",
                        borderRadius: 6,
                    }},
                    {{
                        label: "Gastos",
                        data: {monthly_expense_json},
                        backgroundColor: "rgba(239,68,68,0.8)",
                        borderRadius: 6,
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{ legend: {{ position: "top" }} }},
                scales: {{
                    x: {{ grid: {{ display: false }} }},
                    y: {{ beginAtZero: true, grid: {{ color: "rgba(0,0,0,0.05)" }} }}
                }}
            }}
        }});

        const donutCtx = document.getElementById("donutChart").getContext("2d");
        new Chart(donutCtx, {{
            type: "doughnut",
            data: {{
                labels: {cat_labels_json},
                datasets: [{{
                    data: {cat_values_json},
                    backgroundColor: {cat_colors_json},
                    borderWidth: 2,
                    borderColor: "#ffffff",
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: (ctx) => ` ${{ctx.label}}: ${{ctx.parsed.toLocaleString("es-AR", {{minimumFractionDigits:2}})}}`
                        }}
                    }}
                }},
                cutout: "65%",
            }}
        }});
    </script>
</body>
</html>
"""

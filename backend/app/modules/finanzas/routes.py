import logging
import math
import json

from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.core.security import get_user_id_from_request
from app.core.templates import templates

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
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

    return templates.TemplateResponse(request, "finanzas/dashboard.html", {
        "active_page": "dashboard",
        "balance": balance,
        "total_income": total_income,
        "total_expense": total_expense,
        "month_income": month_income,
        "month_expense": month_expense,
        "month_balance": month_balance,
        "recent_transactions": recent_transactions,
        "upcoming_events": upcoming_events,
        "today_events": today_events,
        "recent_notes": recent_notes,
        "notas_sin_evento": notas_sin_evento,
        "goals": goals,
    })


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
    total_pages = max(1, math.ceil(total / per_page)) if total > 0 else 1

    return templates.TemplateResponse(request, "finanzas/transacciones.html", {
        "active_page": "finanzas",
        "transactions": transactions,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
    })


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

    payment_methods = [
        ("cash", "Efectivo"),
        ("debit_card", "Tarjeta de Débito"),
        ("credit_card", "Tarjeta de Crédito"),
        ("transfer", "Transferencia"),
    ]

    return templates.TemplateResponse(request, "finanzas/transaccion_form.html", {
        "active_page": "finanzas",
        "transaction": None,
        "categories": categories,
        "payment_methods": payment_methods,
        "today_str": date.today().isoformat(),
    })


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

    payment_methods = [
        ("cash", "Efectivo"),
        ("debit_card", "Tarjeta de Débito"),
        ("credit_card", "Tarjeta de Crédito"),
        ("transfer", "Transferencia"),
    ]

    today = transaction.transaction_date
    if hasattr(today, "isoformat"):
        today_str = today.isoformat()
    else:
        today_str = str(today)

    return templates.TemplateResponse(request, "finanzas/transaccion_form.html", {
        "active_page": "finanzas",
        "transaction": transaction,
        "categories": categories,
        "payment_methods": payment_methods,
        "today_str": today_str,
    })


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

    return templates.TemplateResponse(request, "finanzas/categorias.html", {
        "active_page": "finanzas",
        "categories": categories,
    })


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

    monthly_summary = list(zip(month_labels, monthly_income, monthly_expense))
    total_gastos = sum(cat_values)

    return templates.TemplateResponse(request, "finanzas/reportes.html", {
        "active_page": "finanzas",
        "cat_labels": cat_labels,
        "cat_colors": cat_colors,
        "cat_values": cat_values,
        "total_gastos": total_gastos,
        "month_labels": month_labels,
        "monthly_income": monthly_income,
        "monthly_expense": monthly_expense,
        "monthly_summary": monthly_summary,
        "cat_labels_json": json.dumps(cat_labels),
        "cat_colors_json": json.dumps(cat_colors),
        "cat_values_json": json.dumps(cat_values),
        "month_labels_json": json.dumps(month_labels),
        "monthly_income_json": json.dumps(monthly_income),
        "monthly_expense_json": json.dumps(monthly_expense),
    })


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

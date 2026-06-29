from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_user_id_from_request
from app.core.templates import templates
from app.database import get_db
from app.modules.finanzas.models import BankAccount

router = APIRouter(prefix="/finanzas", tags=["finanzas"])

ACCOUNT_TYPE_LABELS = {
    "checking": "Cuenta Corriente",
    "savings": "Caja de Ahorro",
    "credit": "Tarjeta de Crédito",
    "cash": "Efectivo",
    "investment": "Inversión",
}

ACCOUNT_TYPE_ICONS = {
    "checking": "fa-building-columns",
    "savings": "fa-piggy-bank",
    "credit": "fa-credit-card",
    "cash": "fa-money-bill-wave",
    "investment": "fa-chart-line",
}

ACCOUNT_TYPE_COLORS = {
    "checking": "#3B82F6",
    "savings": "#10B981",
    "credit": "#EF4444",
    "cash": "#F59E0B",
    "investment": "#8B5CF6",
}


# ---------------------------------------------------------------------------
# GET /finanzas/cuentas/
# ---------------------------------------------------------------------------

@router.get("/cuentas/")
async def listar_cuentas(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(BankAccount)
        .where(BankAccount.user_id == user_id)
        .order_by(BankAccount.created_at.desc())
    )
    accounts = result.scalars().all()
    total_balance = sum(float(a.balance) for a in accounts)
    return templates.TemplateResponse(request, "finanzas/cuentas.html", {
        "active_page": "finanzas",
        "accounts": accounts,
        "total_balance": total_balance,
        "ACCOUNT_TYPE_LABELS": ACCOUNT_TYPE_LABELS,
        "ACCOUNT_TYPE_ICONS": ACCOUNT_TYPE_ICONS,
        "ACCOUNT_TYPE_COLORS": ACCOUNT_TYPE_COLORS,
    })


# ---------------------------------------------------------------------------
# GET /finanzas/cuentas/nueva
# ---------------------------------------------------------------------------

@router.get("/cuentas/nueva")
async def nueva_cuenta_form(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)
    return templates.TemplateResponse(request, "finanzas/cuenta_form.html", {
        "active_page": "finanzas",
        "account": None,
        "ACCOUNT_TYPE_LABELS": ACCOUNT_TYPE_LABELS,
    })


# ---------------------------------------------------------------------------
# POST /finanzas/cuentas/nueva
# ---------------------------------------------------------------------------

@router.post("/cuentas/nueva")
async def crear_cuenta(
    request: Request,
    db: AsyncSession = Depends(get_db),
    name: str = Form(...),
    bank_name: str = Form(""),
    account_type: str = Form("checking"),
    account_number: str = Form(""),
    last4: str = Form(""),
    currency: str = Form("ARS"),
    balance: str = Form("0"),
):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    try:
        balance_val = float(balance)
    except (ValueError, TypeError):
        balance_val = 0.0

    account = BankAccount(
        id=str(uuid4()),
        user_id=user_id,
        name=name,
        bank_name=bank_name,
        account_type=account_type,
        account_number=account_number,
        last4=last4[-4:] if last4 else "",
        currency=currency,
        balance=balance_val,
    )
    db.add(account)
    await db.commit()
    return RedirectResponse(url="/finanzas/cuentas/", status_code=303)


# ---------------------------------------------------------------------------
# GET /finanzas/cuentas/editar/{id}
# ---------------------------------------------------------------------------

@router.get("/cuentas/editar/{account_id}")
async def editar_cuenta_form(
    request: Request,
    account_id: str,
    db: AsyncSession = Depends(get_db),
):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(BankAccount).where(
            BankAccount.id == account_id,
            BankAccount.user_id == user_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        return RedirectResponse(url="/finanzas/cuentas/", status_code=303)

    return templates.TemplateResponse(request, "finanzas/cuenta_form.html", {
        "active_page": "finanzas",
        "account": account,
        "ACCOUNT_TYPE_LABELS": ACCOUNT_TYPE_LABELS,
    })


# ---------------------------------------------------------------------------
# POST /finanzas/cuentas/editar/{id}
# ---------------------------------------------------------------------------

@router.post("/cuentas/editar/{account_id}")
async def editar_cuenta(
    request: Request,
    account_id: str,
    db: AsyncSession = Depends(get_db),
    name: str = Form(...),
    bank_name: str = Form(""),
    account_type: str = Form("checking"),
    account_number: str = Form(""),
    last4: str = Form(""),
    currency: str = Form("ARS"),
    balance: str = Form("0"),
):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(BankAccount).where(
            BankAccount.id == account_id,
            BankAccount.user_id == user_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        return RedirectResponse(url="/finanzas/cuentas/", status_code=303)

    try:
        balance_val = float(balance)
    except (ValueError, TypeError):
        balance_val = float(account.balance)

    account.name = name
    account.bank_name = bank_name
    account.account_type = account_type
    account.account_number = account_number
    account.last4 = last4[-4:] if last4 else ""
    account.currency = currency
    account.balance = balance_val
    await db.commit()
    return RedirectResponse(url="/finanzas/cuentas/", status_code=303)


# ---------------------------------------------------------------------------
# POST /finanzas/cuentas/eliminar/{id}
# ---------------------------------------------------------------------------

@router.post("/cuentas/eliminar/{account_id}")
async def eliminar_cuenta(
    request: Request,
    account_id: str,
    db: AsyncSession = Depends(get_db),
):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(BankAccount).where(
            BankAccount.id == account_id,
            BankAccount.user_id == user_id,
        )
    )
    account = result.scalar_one_or_none()
    if account:
        await db.delete(account)
        await db.commit()
    return RedirectResponse(url="/finanzas/cuentas/", status_code=303)

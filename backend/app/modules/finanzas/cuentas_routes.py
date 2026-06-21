from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_user_id_from_request
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


def _navbar():
    return """
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
    """


def _head(title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Vida Personal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        * {{ font-family: 'Inter', sans-serif; }}
        .btn-primary {{ background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%); transition: all 0.3s ease; }}
        .btn-primary:hover {{ transform: translateY(-2px); box-shadow: 0 10px 25px -5px rgba(124,58,237,0.4); }}
        .card-shadow {{ box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1); }}
        .input-focus:focus {{ border-color: #7C3AED; box-shadow: 0 0 0 3px rgba(124,58,237,0.1); }}
    </style>
</head>
<body class="bg-[#F8FAFC] min-h-screen">"""


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
    return HTMLResponse(content=render_cuentas(accounts))


# ---------------------------------------------------------------------------
# GET /finanzas/cuentas/nueva
# ---------------------------------------------------------------------------

@router.get("/cuentas/nueva")
async def nueva_cuenta_form(request: Request):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)
    return HTMLResponse(content=render_cuenta_form())


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

    return HTMLResponse(content=render_cuenta_form(account))


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


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def render_cuentas(accounts):
    total_balance = sum(float(a.balance) for a in accounts)

    cards_html = ""
    if not accounts:
        cards_html = """
        <div class="col-span-full text-center py-16 text-[#94A3B8]">
            <i class="fas fa-building-columns text-5xl mb-4 opacity-50"></i>
            <p class="text-lg font-medium">No hay cuentas registradas</p>
            <p class="text-sm mb-6">Agrega tu primera cuenta bancaria</p>
            <a href="/finanzas/cuentas/nueva" class="bg-[#7C3AED] text-white px-5 py-2.5 rounded-xl hover:bg-[#6D28D9] transition font-medium inline-block">
                <i class="fas fa-plus mr-2"></i>Nueva Cuenta
            </a>
        </div>
        """
    else:
        for a in accounts:
            acc_type_label = ACCOUNT_TYPE_LABELS.get(a.account_type, a.account_type)
            icon = ACCOUNT_TYPE_ICONS.get(a.account_type, "fa-wallet")
            color = ACCOUNT_TYPE_COLORS.get(a.account_type, "#7C3AED")
            balance_val = float(a.balance)
            balance_class = "text-green-600" if balance_val >= 0 else "text-red-600"
            last4_display = f"•••• {a.last4}" if a.last4 else ""
            cards_html += f"""
            <div class="bg-white rounded-2xl p-6 card-shadow border border-gray-100 flex flex-col gap-4">
                <div class="flex items-start justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-12 h-12 rounded-xl flex items-center justify-center" style="background-color: {color}20;">
                            <i class="fas {icon} text-xl" style="color: {color};"></i>
                        </div>
                        <div>
                            <p class="font-semibold text-[#1E293B]">{a.name}</p>
                            <p class="text-xs text-[#94A3B8]">{a.bank_name or acc_type_label}</p>
                        </div>
                    </div>
                    <div class="flex items-center gap-1">
                        <a href="/finanzas/cuentas/editar/{a.id}" class="p-2 rounded-lg text-[#94A3B8] hover:text-[#7C3AED] hover:bg-[#EDE9FE] transition">
                            <i class="fas fa-pen text-xs"></i>
                        </a>
                        <form action="/finanzas/cuentas/eliminar/{a.id}" method="POST"
                              onsubmit="return confirm('¿Eliminar esta cuenta?');">
                            <button type="submit" class="p-2 rounded-lg text-[#94A3B8] hover:text-red-500 hover:bg-red-50 transition">
                                <i class="fas fa-trash-alt text-xs"></i>
                            </button>
                        </form>
                    </div>
                </div>
                <div>
                    <p class="text-xs text-[#94A3B8] uppercase tracking-wider mb-1">Saldo</p>
                    <p class="text-2xl font-bold {balance_class}">{a.currency} {balance_val:,.2f}</p>
                    {f'<p class="text-xs text-[#94A3B8] mt-1">{last4_display}</p>' if last4_display else ""}
                </div>
                <div class="pt-2 border-t border-gray-50">
                    <span class="px-2.5 py-1 rounded-full text-xs font-medium bg-[#F1F5F9] text-[#64748B]">{acc_type_label}</span>
                </div>
            </div>
            """

    return f"""{_head("Cuentas Bancarias")}
{_navbar()}
<main class="max-w-7xl mx-auto px-6 py-10">
    <div class="flex justify-between items-center mb-8">
        <div>
            <a href="/finanzas/" class="text-[#64748B] hover:text-[#7C3AED] transition text-sm mb-2 inline-flex items-center gap-1">
                <i class="fas fa-arrow-left"></i> Volver al Dashboard
            </a>
            <h1 class="text-3xl font-bold text-[#1E293B]">Cuentas Bancarias</h1>
            <p class="text-[#64748B] mt-1">Balance total: <span class="font-semibold text-[#1E293B]">ARS {total_balance:,.2f}</span></p>
        </div>
        <a href="/finanzas/cuentas/nueva" class="bg-[#7C3AED] text-white px-5 py-2.5 rounded-xl hover:bg-[#6D28D9] transition font-medium flex items-center gap-2">
            <i class="fas fa-plus"></i>Nueva Cuenta
        </a>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {cards_html}
    </div>
</main>
</body>
</html>
"""


def render_cuenta_form(account=None):
    is_edit = account is not None
    title = "Editar Cuenta" if is_edit else "Nueva Cuenta"
    action = f"/finanzas/cuentas/editar/{account.id}" if is_edit else "/finanzas/cuentas/nueva"

    name_val = account.name if is_edit else ""
    bank_name_val = account.bank_name if is_edit else ""
    account_number_val = account.account_number if is_edit else ""
    last4_val = account.last4 if is_edit else ""
    currency_val = account.currency if is_edit else "ARS"
    balance_val = str(float(account.balance)) if is_edit else "0"

    account_type_options = ""
    for val, label in ACCOUNT_TYPE_LABELS.items():
        selected = "selected" if is_edit and account.account_type == val else (
            "selected" if not is_edit and val == "checking" else ""
        )
        account_type_options += f'<option value="{val}" {selected}>{label}</option>'

    currency_options = ""
    for c in ["ARS", "USD", "EUR", "BRL"]:
        selected = "selected" if currency_val == c else ""
        currency_options += f'<option value="{c}" {selected}>{c}</option>'

    return f"""{_head(title)}
{_navbar()}
<main class="max-w-2xl mx-auto px-6 py-10">
    <a href="/finanzas/cuentas/" class="text-[#64748B] hover:text-[#7C3AED] transition text-sm mb-4 inline-flex items-center gap-1">
        <i class="fas fa-arrow-left"></i> Volver a Cuentas
    </a>

    <div class="bg-white rounded-2xl p-8 card-shadow border border-gray-100 mt-4">
        <h1 class="text-2xl font-bold text-[#1E293B] mb-6">{title}</h1>

        <form method="POST" action="{action}" class="space-y-5">
            <div>
                <label class="block text-sm font-medium text-[#374151] mb-2">Nombre de la cuenta</label>
                <input type="text" name="name" required value="{name_val}"
                    class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                    placeholder="Ej: Cuenta Sueldo, Tarjeta Visa...">
            </div>

            <div class="grid grid-cols-2 gap-5">
                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Tipo de cuenta</label>
                    <select name="account_type"
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none">
                        {account_type_options}
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Banco / Entidad</label>
                    <input type="text" name="bank_name" value="{bank_name_val}"
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                        placeholder="Ej: Santander, Naranja X...">
                </div>
            </div>

            <div class="grid grid-cols-2 gap-5">
                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Número de cuenta (opcional)</label>
                    <input type="text" name="account_number" value="{account_number_val}"
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                        placeholder="Número de cuenta">
                </div>
                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Últimos 4 dígitos (opcional)</label>
                    <input type="text" name="last4" value="{last4_val}" maxlength="4"
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                        placeholder="1234">
                </div>
            </div>

            <div class="grid grid-cols-2 gap-5">
                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Moneda</label>
                    <select name="currency"
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none">
                        {currency_options}
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Saldo actual</label>
                    <div class="relative">
                        <span class="absolute left-4 top-1/2 -translate-y-1/2 text-[#64748B]">$</span>
                        <input type="number" name="balance" step="0.01" value="{balance_val}"
                            class="w-full pl-8 pr-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                            placeholder="0.00">
                    </div>
                </div>
            </div>

            <div class="flex gap-4 pt-4 border-t border-gray-100">
                <button type="submit" class="btn-primary text-white px-8 py-3 rounded-xl font-medium flex items-center gap-2">
                    <i class="fas fa-check"></i>{'Guardar Cambios' if is_edit else 'Crear Cuenta'}
                </button>
                <a href="/finanzas/cuentas/" class="px-8 py-3 rounded-xl font-medium bg-gray-100 text-[#64748B] hover:bg-gray-200 transition">
                    Cancelar
                </a>
            </div>
        </form>
    </div>
</main>
</body>
</html>
"""

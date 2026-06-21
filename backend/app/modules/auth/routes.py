from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


async def _get_theme(user_id: str, db) -> str:
    from app.modules.ajustes.models import UserPreference
    from sqlalchemy import select as sa_select

    result = await db.execute(
        sa_select(UserPreference.theme_color).where(UserPreference.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    return row or "violet"


def _set_auth_cookie(response: RedirectResponse, user_id: str, theme: str = "violet") -> None:
    token = create_access_token({"sub": str(user_id), "theme": theme})
    response.set_cookie(
        key=settings.JWT_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=not settings.DEBUG,
    )


@router.get("/login")
async def login_page(request: Request):
    return HTMLResponse(content=render_login())


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.auth.models import User
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        return HTMLResponse(
            content=render_login(error="Email o contraseña incorrectos"),
            status_code=400,
        )

    # Upgrade legacy SHA256 hash to bcrypt transparently
    if not user.password_hash.startswith("$2"):
        user.password_hash = hash_password(password)
        db.add(user)
        await db.commit()

    theme = await _get_theme(user.id, db)
    response = RedirectResponse(url="/finanzas/", status_code=303)
    _set_auth_cookie(response, user.id, theme)
    return response


@router.get("/register")
async def register_page(request: Request):
    return HTMLResponse(content=render_register())


@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if password != password_confirm:
        return HTMLResponse(
            content=render_register(error="Las contraseñas no coinciden"),
            status_code=400,
        )

    if len(password) < 8:
        return HTMLResponse(
            content=render_register(
                error="La contraseña debe tener al menos 8 caracteres"
            ),
            status_code=400,
        )

    from app.modules.auth.models import User
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()

    if existing:
        return HTMLResponse(
            content=render_register(error="Este email ya está registrado"),
            status_code=400,
        )

    user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    response = RedirectResponse(url="/finanzas/", status_code=303)
    _set_auth_cookie(response, user.id, "violet")
    return response


@router.post("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie(settings.JWT_COOKIE_NAME)
    return response


@router.get("/logout")
async def logout_get(request: Request):
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie(settings.JWT_COOKIE_NAME)
    return response


def render_login(error=None):
    error_html = (
        f'<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">{error}</div>'
        if error
        else ""
    )
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Iniciar Sesion - Vida Personal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center">
    <div class="bg-white p-8 rounded-lg shadow-lg w-full max-w-md">
        <div class="text-center mb-8">
            <h1 class="text-3xl font-bold text-gray-800">
                <i class="fas fa-home text-indigo-600 mr-2"></i>Vida Personal
            </h1>
            <p class="text-gray-500 mt-2">Ingresa a tu cuenta</p>
        </div>
        {error_html}
        <form method="POST" action="/auth/login" class="space-y-6">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input type="email" name="email" required class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="tu@email.com" autofocus>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
                <input type="password" name="password" required class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="Tu contraseña">
            </div>
            <button type="submit" class="w-full bg-indigo-600 text-white py-3 rounded-md hover:bg-indigo-700 transition font-medium">
                <i class="fas fa-sign-in-alt mr-2"></i>Iniciar Sesion
            </button>
        </form>
        <div class="mt-6 text-center">
            <p class="text-gray-600">No tienes cuenta? <a href="/auth/register" class="text-indigo-600 hover:text-indigo-800 font-medium">Registrate aqui</a></p>
        </div>
    </div>
</body>
</html>
"""


def render_register(error=None):
    error_html = (
        f'<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">{error}</div>'
        if error
        else ""
    )
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Registrarse - Vida Personal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center">
    <div class="bg-white p-8 rounded-lg shadow-lg w-full max-w-md">
        <div class="text-center mb-8">
            <h1 class="text-3xl font-bold text-gray-800">
                <i class="fas fa-user-plus text-indigo-600 mr-2"></i>Crear Cuenta
            </h1>
            <p class="text-gray-500 mt-2">Completa tus datos para registrarte</p>
        </div>
        {error_html}
        <form method="POST" action="/auth/register" class="space-y-5">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Nombre Completo</label>
                <input type="text" name="full_name" required class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="Tu nombre" autofocus>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input type="email" name="email" required class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="tu@email.com">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
                <input type="password" name="password" required minlength="8" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="Mínimo 8 caracteres">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Confirmar Contraseña</label>
                <input type="password" name="password_confirm" required class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="Repite tu contraseña">
            </div>
            <button type="submit" class="w-full bg-indigo-600 text-white py-3 rounded-md hover:bg-indigo-700 transition font-medium">
                <i class="fas fa-user-plus mr-2"></i>Crear Cuenta
            </button>
        </form>
        <div class="mt-6 text-center">
            <p class="text-gray-600">Ya tienes cuenta? <a href="/auth/login" class="text-indigo-600 hover:text-indigo-800 font-medium">Inicia sesion</a></p>
        </div>
    </div>
</body>
</html>
"""

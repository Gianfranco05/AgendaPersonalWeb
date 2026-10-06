from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.core.http_security import rate_limit_auth
from app.core.templates import templates

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
    # TTL propio (largo): este flujo no puede refrescar el token, ver
    # LEGACY_HTML_SESSION_EXPIRE_MINUTES en config.py.
    ttl_minutes = settings.LEGACY_HTML_SESSION_EXPIRE_MINUTES
    token = create_access_token(
        {"sub": str(user_id), "theme": theme},
        expires_delta=timedelta(minutes=ttl_minutes),
    )
    response.set_cookie(
        key=settings.JWT_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=ttl_minutes * 60,
        samesite="lax",
        secure=not settings.DEBUG,
    )


async def _issue_refresh_cookie(
    response: RedirectResponse, request: Request, user_id: str, db
) -> None:
    """Registra la sesion HTML como refresh token.

    El flujo HTML no lo usa para refrescar (no tiene interceptor), pero asi la
    sesion aparece en GET /auth/api/sessions y el logout puede revocarla igual
    que las de la SPA o mobile.
    """
    from app.modules.auth.refresh_service import RefreshService

    raw = await RefreshService(db).issue(
        str(user_id), device_info=request.headers.get("User-Agent")
    )
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=raw,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        samesite="lax",
        secure=not settings.DEBUG,
    )


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "auth/login.html", {"error": None})


@router.post("/login", dependencies=[Depends(rate_limit_auth)])
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
        return templates.TemplateResponse(request, "auth/login.html", {"error": "Email o contraseña incorrectos"}, status_code=400)

    # Igual que en /auth/api/login: una cuenta desactivada no entra. Sin esto
    # este flujo le daba una cookie de 24h que las rutas HTML aceptan.
    if not user.is_active:
        return templates.TemplateResponse(request, "auth/login.html", {"error": "Usuario inactivo"}, status_code=403)

    if not user.password_hash.startswith("$2"):
        user.password_hash = hash_password(password)
        db.add(user)
        await db.commit()

    theme = await _get_theme(user.id, db)
    response = RedirectResponse(url="/finanzas/", status_code=303)
    _set_auth_cookie(response, user.id, theme)
    await _issue_refresh_cookie(response, request, user.id, db)
    return response


@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(request, "auth/register.html", {"error": None})


@router.post("/register", dependencies=[Depends(rate_limit_auth)])
async def register(
    request: Request,
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if password != password_confirm:
        return templates.TemplateResponse(request, "auth/register.html", {"error": "Las contraseñas no coinciden"}, status_code=400)

    if len(password) < 8:
        return templates.TemplateResponse(request, "auth/register.html", {"error": "La contraseña debe tener al menos 8 caracteres"}, status_code=400)

    from app.modules.auth.models import User
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()

    if existing:
        return templates.TemplateResponse(request, "auth/register.html", {"error": "Este email ya está registrado"}, status_code=400)

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
    await _issue_refresh_cookie(response, request, user.id, db)
    return response


async def _logout_response(request: Request, db) -> RedirectResponse:
    from app.modules.auth.refresh_service import RefreshService

    raw = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if raw:
        await RefreshService(db).revoke(raw)
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie(settings.JWT_COOKIE_NAME)
    response.delete_cookie(settings.REFRESH_COOKIE_NAME)
    return response


@router.post("/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    return await _logout_response(request, db)


@router.get("/logout")
async def logout_get(request: Request, db: AsyncSession = Depends(get_db)):
    return await _logout_response(request, db)

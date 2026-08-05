import asyncio
import secrets

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    create_access_token,
    get_user_id_from_request,
)
from app.core.templates import templates
from app.database import get_db
from app.modules.ajustes.service import SettingsService
from app.modules.ajustes.models import UserPreference
from app.modules.ajustes.schemas import UserPreferenceOut, UserPreferenceUpdate

router = APIRouter(prefix="/ajustes", tags=["ajustes"])

THEME_COLORS = {
    "violet": "#7C3AED",
    "indigo": "#6366F1",
    "blue": "#3B82F6",
    "emerald": "#10B981",
    "rose": "#F43F5E",
    "amber": "#F59E0B",
}

CURRENCIES = ["ARS", "USD", "EUR", "BRL", "CLP", "UYU"]

DATE_FORMATS = [("DD/MM/YYYY", "31/12/2024"), ("MM/DD/YYYY", "12/31/2024"), ("YYYY-MM-DD", "2024-12-31")]


def _make_auth_response(url: str, user_id: str, theme_color: str) -> RedirectResponse:
    response = RedirectResponse(url=url, status_code=303)
    token = create_access_token({"sub": user_id, "theme": theme_color})
    response.set_cookie(
        key=settings.JWT_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=not settings.DEBUG,
    )
    return response


@router.get("/")
async def ajustes_page(
    request: Request,
    success: str | None = None,
    error: str | None = None,
    synced: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    from app.modules.auth.models import User

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    service = SettingsService(db)
    prefs = await service.get_preferences(user_id)
    google_configured = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
    google_connected = bool(prefs.google_refresh_token)

    alert_message = None
    alert_bg = ""
    alert_icon = ""
    alert_icon_color = ""

    if success == "saved":
        alert_message = "Preferencias guardadas correctamente."
        alert_bg = "bg-green-50 border-green-200 text-green-800"
        alert_icon = "check-circle"
        alert_icon_color = "text-green-500"
    elif success == "google_connected":
        alert_message = "Google Calendar conectado exitosamente."
        alert_bg = "bg-green-50 border-green-200 text-green-800"
        alert_icon = "check-circle"
        alert_icon_color = "text-green-500"
    elif success == "google_disconnected":
        alert_message = "Google Calendar desconectado."
        alert_bg = "bg-blue-50 border-blue-200 text-blue-800"
        alert_icon = "info-circle"
        alert_icon_color = "text-blue-500"
    elif synced is not None:
        alert_message = f"{synced} evento(s) sincronizado(s) con Google Calendar."
        alert_bg = "bg-green-50 border-green-200 text-green-800"
        alert_icon = "check-circle"
        alert_icon_color = "text-green-500"
    elif error == "google_not_configured":
        alert_message = "Configurá GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET en el .env para usar esta función."
        alert_bg = "bg-yellow-50 border-yellow-200 text-yellow-800"
        alert_icon = "exclamation-triangle"
        alert_icon_color = "text-yellow-500"
    elif error == "google_denied":
        alert_message = "Acceso a Google Calendar denegado."
        alert_bg = "bg-red-50 border-red-200 text-red-800"
        alert_icon = "exclamation-circle"
        alert_icon_color = "text-red-500"
    elif error == "sync_failed":
        alert_message = "Error al sincronizar con Google Calendar. Verificá la conexión."
        alert_bg = "bg-red-50 border-red-200 text-red-800"
        alert_icon = "exclamation-circle"
        alert_icon_color = "text-red-500"
    elif error == "not_connected":
        alert_message = "Primero conectá tu cuenta de Google Calendar."
        alert_bg = "bg-yellow-50 border-yellow-200 text-yellow-800"
        alert_icon = "exclamation-triangle"
        alert_icon_color = "text-yellow-500"
    elif error:
        alert_message = f"Error: {error}"
        alert_bg = "bg-red-50 border-red-200 text-red-800"
        alert_icon = "exclamation-circle"
        alert_icon_color = "text-red-500"

    user_name = user.full_name if user else "Usuario"
    user_email = user.email if user else ""

    return templates.TemplateResponse(request, "ajustes/preferencias.html", {
        "active_page": "ajustes",
        "user": user,
        "user_name": user_name,
        "user_email": user_email,
        "prefs": prefs,
        "google_configured": google_configured,
        "google_connected": google_connected,
        "alert_message": alert_message,
        "alert_bg": alert_bg,
        "alert_icon": alert_icon,
        "alert_icon_color": alert_icon_color,
        "theme_colors": THEME_COLORS,
        "currencies": CURRENCIES,
        "date_formats": DATE_FORMATS,
    })


@router.post("/")
async def save_ajustes(
    request: Request,
    currency: str = Form("ARS"),
    theme_color: str = Form("violet"),
    date_format: str = Form("DD/MM/YYYY"),
    db: AsyncSession = Depends(get_db),
):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    if theme_color not in THEME_COLORS:
        theme_color = "violet"
    if currency not in CURRENCIES:
        currency = "ARS"

    service = SettingsService(db)
    data = UserPreferenceUpdate(
        currency=currency,
        theme_color=theme_color,
        date_format=date_format,
    )
    await service.update_preferences(user_id, data)

    return _make_auth_response("/ajustes/?success=saved", user_id, theme_color)


@router.get("/api/preferences", response_model=UserPreferenceOut)
async def api_preferences(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    service = SettingsService(db)
    prefs = await service.get_preferences(user_id)
    return prefs


@router.get("/google/connect")
async def google_connect(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return RedirectResponse(url=_frontend_redirect("/settings?google_error=google_not_configured"), status_code=303)

    from google_auth_oauthlib.flow import Flow

    flow = _build_google_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    response = RedirectResponse(url=auth_url, status_code=303)
    response.set_cookie("oauth_state", state, httponly=True, max_age=300, samesite="lax")
    return response


def _frontend_redirect(path: str) -> str:
    return f"{settings.FRONTEND_URL}{path}"


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    if error:
        return RedirectResponse(url=_frontend_redirect("/settings?google_error=google_denied"), status_code=303)

    stored_state = request.cookies.get("oauth_state")
    if not state or state != stored_state:
        return RedirectResponse(url=_frontend_redirect("/settings?google_error=invalid_state"), status_code=303)

    if not code:
        return RedirectResponse(url=_frontend_redirect("/settings?google_error=no_code"), status_code=303)

    try:
        flow = _build_google_flow()
        await asyncio.to_thread(flow.fetch_token, code=code)
        credentials = flow.credentials

        service = SettingsService(db)
        prefs = await service.get_preferences(user_id)
        prefs.google_access_token = credentials.token
        prefs.google_refresh_token = credentials.refresh_token or prefs.google_refresh_token
        prefs.google_token_expiry = credentials.expiry
        db.add(prefs)
        await db.commit()
    except Exception:
        return RedirectResponse(url=_frontend_redirect("/settings?google_error=google_exchange_failed"), status_code=303)

    response = RedirectResponse(url=_frontend_redirect("/settings?google=connected"), status_code=303)
    response.delete_cookie("oauth_state")
    return response


@router.post("/google/disconnect")
async def google_disconnect(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    service = SettingsService(db)
    await service.disconnect_google(user_id)

    return RedirectResponse(url="/ajustes/?success=google_disconnected", status_code=303)


@router.post("/google/sync")
async def google_sync(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    service = SettingsService(db)
    prefs = await service.get_preferences(user_id)
    if not prefs.google_refresh_token:
        return RedirectResponse(url="/ajustes/?error=not_connected", status_code=303)

    try:
        count = await service.sync_events_to_google(user_id, prefs)
    except Exception:
        return RedirectResponse(url="/ajustes/?error=sync_failed", status_code=303)

    return RedirectResponse(url=f"/ajustes/?synced={count}", status_code=303)


def _build_google_flow():
    from google_auth_oauthlib.flow import Flow

    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=["https://www.googleapis.com/auth/calendar.events"],
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )

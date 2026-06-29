import asyncio
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    create_access_token,
    get_user_id_from_request,
)
from app.database import get_db
from app.modules.ajustes.models import UserPreference
from app.modules.ajustes.service import SettingsService
from app.modules.ajustes.schemas import UserPreferenceUpdate, UserPreferenceOut

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

    return HTMLResponse(
        content=render_ajustes(
            user=user,
            prefs=prefs,
            google_configured=google_configured,
            google_connected=google_connected,
            success=success,
            error=error,
            synced=synced,
        )
    )


@router.get("/api/preferences")
async def api_preferences(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)
    service = SettingsService(db)
    prefs = await service.get_preferences(user_id)
    return {
        "id": prefs.id,
        "user_id": prefs.user_id,
        "currency": prefs.currency,
        "theme_color": prefs.theme_color,
        "date_format": prefs.date_format,
        "google_calendar_id": prefs.google_calendar_id,
        "google_connected": bool(prefs.google_refresh_token),
        "created_at": prefs.created_at.isoformat() if prefs.created_at else None,
        "updated_at": prefs.updated_at.isoformat() if prefs.updated_at else None,
    }


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
    await service.update_preferences(
        user_id,
        UserPreferenceUpdate(
            currency=currency,
            theme_color=theme_color,
            date_format=date_format,
        ),
    )

    return _make_auth_response("/ajustes/?success=saved", user_id, theme_color)


# ── Google Calendar OAuth ─────────────────────────────────────────────────────

@router.get("/google/connect")
async def google_connect(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return RedirectResponse(url="/ajustes/?error=google_not_configured", status_code=303)

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
        return RedirectResponse(url="/ajustes/?error=google_denied", status_code=303)

    stored_state = request.cookies.get("oauth_state")
    if not state or state != stored_state:
        return RedirectResponse(url="/ajustes/?error=invalid_state", status_code=303)

    if not code:
        return RedirectResponse(url="/ajustes/?error=no_code", status_code=303)

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
        return RedirectResponse(url="/ajustes/?error=google_exchange_failed", status_code=303)

    response = RedirectResponse(url="/ajustes/?success=google_connected", status_code=303)
    response.delete_cookie("oauth_state")
    return response


@router.post("/google/disconnect")
async def google_disconnect(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    service = SettingsService(db)
    prefs = await service.get_preferences(user_id)
    prefs.google_access_token = None
    prefs.google_refresh_token = None
    prefs.google_token_expiry = None
    db.add(prefs)
    await db.commit()

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
        count = await _sync_events_to_google(user_id, prefs, db)
    except Exception as e:
        return RedirectResponse(url=f"/ajustes/?error=sync_failed", status_code=303)

    return RedirectResponse(url=f"/ajustes/?synced={count}", status_code=303)


# ── Helpers ───────────────────────────────────────────────────────────────────

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


async def _sync_events_to_google(
    user_id: str, prefs: UserPreference, db: AsyncSession
) -> int:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request as GRequest
    from googleapiclient.discovery import build
    from app.modules.eventos.models import Event

    creds = Credentials(
        token=prefs.google_access_token,
        refresh_token=prefs.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

    if creds.expired and creds.refresh_token:
        await asyncio.to_thread(creds.refresh, GRequest())
        prefs.google_access_token = creds.token
        prefs.google_token_expiry = creds.expiry
        db.add(prefs)
        await db.commit()

    service = await asyncio.to_thread(build, "calendar", "v3", credentials=creds)

    events_result = await db.execute(select(Event).where(Event.user_id == user_id))
    events = events_result.scalars().all()

    synced = 0
    for event in events:
        end_dt = event.end_datetime or (event.start_datetime + timedelta(hours=1))
        g_event = {
            "summary": event.title,
            "description": event.description or "",
            "start": {
                "dateTime": event.start_datetime.isoformat(),
                "timeZone": "America/Argentina/Buenos_Aires",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "America/Argentina/Buenos_Aires",
            },
        }
        if event.location:
            g_event["location"] = event.location
        if event.is_all_day:
            date_str = event.start_datetime.strftime("%Y-%m-%d")
            g_event["start"] = {"date": date_str}
            g_event["end"] = {"date": date_str}

        await asyncio.to_thread(
            service.events().insert(calendarId=prefs.google_calendar_id, body=g_event).execute
        )
        synced += 1

    return synced


# ── HTML ──────────────────────────────────────────────────────────────────────

def render_ajustes(user, prefs, google_configured, google_connected, success=None, error=None, synced=None):
    alert_html = ""
    if success == "saved":
        alert_html = _alert("Preferencias guardadas correctamente.", "green")
    elif success == "google_connected":
        alert_html = _alert("Google Calendar conectado exitosamente.", "green")
    elif success == "google_disconnected":
        alert_html = _alert("Google Calendar desconectado.", "blue")
    elif synced is not None:
        alert_html = _alert(f"{synced} evento(s) sincronizado(s) con Google Calendar.", "green")
    elif error == "google_not_configured":
        alert_html = _alert("Configurá GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET en el .env para usar esta función.", "yellow")
    elif error == "google_denied":
        alert_html = _alert("Acceso a Google Calendar denegado.", "red")
    elif error == "sync_failed":
        alert_html = _alert("Error al sincronizar con Google Calendar. Verificá la conexión.", "red")
    elif error == "not_connected":
        alert_html = _alert("Primero conectá tu cuenta de Google Calendar.", "yellow")
    elif error:
        alert_html = _alert(f"Error: {error}", "red")

    # Theme swatches
    theme_swatches = ""
    for key, hex_color in THEME_COLORS.items():
        labels = {
            "violet": "Violeta", "indigo": "Índigo", "blue": "Azul",
            "emerald": "Verde", "rose": "Rosa", "amber": "Ámbar"
        }
        checked = "ring-4 ring-offset-2 ring-gray-400 scale-110" if prefs.theme_color == key else ""
        theme_swatches += f"""
        <label class="cursor-pointer flex flex-col items-center gap-2 group">
            <input type="radio" name="theme_color" value="{key}" {"checked" if prefs.theme_color == key else ""}
                   class="sr-only" onchange="this.form.submit()">
            <div class="w-10 h-10 rounded-full transition-all duration-200 {checked}"
                 style="background-color:{hex_color};"></div>
            <span class="text-xs text-[#64748B] group-hover:text-[#1E293B] transition">{labels[key]}</span>
        </label>"""

    # Currency options
    currency_options = "".join(
        f'<option value="{c}" {"selected" if prefs.currency == c else ""}>{c}</option>'
        for c in CURRENCIES
    )

    # Date format options
    date_formats = [("DD/MM/YYYY", "31/12/2024"), ("MM/DD/YYYY", "12/31/2024"), ("YYYY-MM-DD", "2024-12-31")]
    date_format_options = "".join(
        f'<option value="{fmt}" {"selected" if prefs.date_format == fmt else ""}>{fmt} — ej: {ex}</option>'
        for fmt, ex in date_formats
    )

    # Google Calendar section
    if not google_configured:
        google_html = """
        <div class="flex items-start gap-4 p-4 bg-yellow-50 rounded-xl border border-yellow-200">
            <i class="fas fa-info-circle text-yellow-500 mt-0.5 text-lg"></i>
            <div>
                <p class="font-medium text-[#1E293B] text-sm">Integración no configurada</p>
                <p class="text-xs text-[#64748B] mt-1">
                    Para conectar Google Calendar, configurá las variables
                    <code class="bg-yellow-100 px-1 rounded">GOOGLE_CLIENT_ID</code> y
                    <code class="bg-yellow-100 px-1 rounded">GOOGLE_CLIENT_SECRET</code> en tu <code class="bg-yellow-100 px-1 rounded">.env</code>.
                    <a href="https://console.cloud.google.com/" target="_blank" class="text-[#7C3AED] hover:underline ml-1">Google Cloud Console →</a>
                </p>
            </div>
        </div>"""
    elif google_connected:
        google_html = f"""
        <div class="flex items-center justify-between p-4 bg-green-50 rounded-xl border border-green-200">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center">
                    <i class="fab fa-google text-green-600"></i>
                </div>
                <div>
                    <p class="font-semibold text-[#1E293B] text-sm">Google Calendar conectado</p>
                    <p class="text-xs text-green-600">Calendario: {prefs.google_calendar_id}</p>
                </div>
            </div>
            <div class="flex items-center gap-2">
                <form method="POST" action="/ajustes/google/sync">
                    <button type="submit"
                            class="px-4 py-2 bg-[#7C3AED] text-white text-sm rounded-lg hover:bg-[#6D28D9] transition font-medium flex items-center gap-2">
                        <i class="fas fa-sync-alt"></i>Sincronizar eventos
                    </button>
                </form>
                <form method="POST" action="/ajustes/google/disconnect"
                      onsubmit="return confirm('¿Desconectar Google Calendar?');">
                    <button type="submit"
                            class="px-4 py-2 bg-white text-red-500 text-sm rounded-lg border border-red-200 hover:bg-red-50 transition font-medium">
                        <i class="fas fa-unlink mr-1"></i>Desconectar
                    </button>
                </form>
            </div>
        </div>"""
    else:
        google_html = """
        <div class="flex items-center justify-between p-4 bg-gray-50 rounded-xl border border-gray-200">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-white border border-gray-200 flex items-center justify-center">
                    <i class="fab fa-google text-gray-400"></i>
                </div>
                <div>
                    <p class="font-semibold text-[#1E293B] text-sm">Google Calendar</p>
                    <p class="text-xs text-[#94A3B8]">No conectado — sincronizá tus eventos automáticamente</p>
                </div>
            </div>
            <a href="/ajustes/google/connect"
               class="px-4 py-2 bg-[#7C3AED] text-white text-sm rounded-lg hover:bg-[#6D28D9] transition font-medium flex items-center gap-2">
                <i class="fab fa-google"></i>Conectar
            </a>
        </div>"""

    user_name = user.full_name if user else "Usuario"
    user_email = user.email if user else ""

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ajustes - Vida Personal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
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
                    <a href="/ajustes/" class="px-5 py-2.5 rounded-xl bg-[#7C3AED] text-sm font-medium">Ajustes</a>
                    <div class="w-px h-8 bg-white/20 mx-2"></div>
                    <a href="/auth/logout" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">
                        <i class="fas fa-sign-out-alt mr-2"></i>Salir
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-3xl mx-auto px-6 py-10">
        <div class="mb-8">
            <a href="/finanzas/" class="text-[#64748B] hover:text-[#7C3AED] transition text-sm mb-2 inline-flex items-center gap-1">
                <i class="fas fa-arrow-left"></i>Volver al Dashboard
            </a>
            <h1 class="text-3xl font-bold text-[#1E293B]">Ajustes</h1>
            <p class="text-[#64748B] mt-1">Personalizá la aplicación a tu gusto</p>
        </div>

        {alert_html}

        <!-- Perfil -->
        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
            <h2 class="text-lg font-semibold text-[#1E293B] mb-4 flex items-center gap-2">
                <i class="fas fa-user-circle text-[#7C3AED]"></i>Perfil
            </h2>
            <div class="flex items-center gap-4">
                <div class="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#7C3AED] to-[#22D3EE] flex items-center justify-center text-white text-xl font-bold">
                    {user_name[0].upper() if user_name else "?"}
                </div>
                <div>
                    <p class="font-semibold text-[#1E293B]">{user_name}</p>
                    <p class="text-sm text-[#64748B]">{user_email}</p>
                </div>
            </div>
        </div>

        <!-- Preferencias -->
        <form method="POST" action="/ajustes/" id="prefs-form">
            <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
                <h2 class="text-lg font-semibold text-[#1E293B] mb-5 flex items-center gap-2">
                    <i class="fas fa-sliders text-[#7C3AED]"></i>Preferencias
                </h2>
                <div class="grid grid-cols-2 gap-5">
                    <div>
                        <label class="block text-sm font-medium text-[#374151] mb-1.5">Moneda por defecto</label>
                        <select name="currency"
                                class="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#7C3AED]/40 focus:border-[#7C3AED]">
                            {currency_options}
                        </select>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-[#374151] mb-1.5">Formato de fecha</label>
                        <select name="date_format"
                                class="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#7C3AED]/40 focus:border-[#7C3AED]">
                            {date_format_options}
                        </select>
                    </div>
                </div>
            </div>

            <!-- Apariencia -->
            <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
                <h2 class="text-lg font-semibold text-[#1E293B] mb-5 flex items-center gap-2">
                    <i class="fas fa-palette text-[#7C3AED]"></i>Apariencia
                </h2>
                <p class="text-sm text-[#64748B] mb-4">Color de acento de la interfaz</p>
                <div class="flex items-center gap-6">
                    {theme_swatches}
                </div>
            </div>

            <div class="flex justify-end">
                <button type="submit"
                        class="px-6 py-3 bg-[#7C3AED] text-white rounded-xl font-semibold hover:bg-[#6D28D9] transition shadow-sm flex items-center gap-2">
                    <i class="fas fa-save"></i>Guardar cambios
                </button>
            </div>
        </form>

        <!-- Integraciones -->
        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mt-6">
            <h2 class="text-lg font-semibold text-[#1E293B] mb-2 flex items-center gap-2">
                <i class="fas fa-plug text-[#7C3AED]"></i>Integraciones
            </h2>
            <p class="text-sm text-[#64748B] mb-5">Conectá servicios externos para ampliar las funcionalidades</p>

            {google_html}
        </div>
    </main>
</body>
</html>
"""


def _alert(message: str, color: str) -> str:
    icons = {"green": "check-circle", "red": "exclamation-circle", "yellow": "exclamation-triangle", "blue": "info-circle"}
    bg = {"green": "bg-green-50 border-green-200 text-green-800", "red": "bg-red-50 border-red-200 text-red-800",
          "yellow": "bg-yellow-50 border-yellow-200 text-yellow-800", "blue": "bg-blue-50 border-blue-200 text-blue-800"}
    icon_color = {"green": "text-green-500", "red": "text-red-500", "yellow": "text-yellow-500", "blue": "text-blue-500"}
    return f"""
    <div class="{bg.get(color, bg['blue'])} border rounded-xl p-4 mb-6 flex items-center gap-3">
        <i class="fas fa-{icons.get(color, 'info-circle')} {icon_color.get(color, '')}"></i>
        <p class="text-sm font-medium">{message}</p>
    </div>"""

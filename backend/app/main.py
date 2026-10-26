import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import hmac

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import generate_latest

from app.config import settings
from app.database import engine
from app.core.security import decode_access_token
from app.core.error_handlers import register_error_handlers
from app.core.sentry import init_sentry
from app.core.correlation import CorrelationMiddleware
from app.core.request_logging import RequestLoggingMiddleware
from app.core.metrics import PrometheusMiddleware
from app.core.http_security import BodySizeLimitMiddleware, SecurityHeadersMiddleware
from app.core.logging_config import setup_logging
from app.core.health import health_router
from app.modules.recordatorios.scheduler import run_reminder_scheduler
from app.modules.inversiones.scheduler import run_investment_alert_scheduler
from app.modules.mercado.scheduler import run_market_data_scheduler

logger = logging.getLogger(__name__)

# Primary accent color used in all existing render functions
_DEFAULT_HEX = "#7C3AED"
_THEME_COLORS = {
    "violet": "#7C3AED",
    "indigo": "#6366F1",
    "blue": "#3B82F6",
    "emerald": "#10B981",
    "rose": "#F43F5E",
    "amber": "#F59E0B",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_sentry()
    logger.info("Sentry initialized")
    scheduler_tasks = [
        asyncio.create_task(run_reminder_scheduler()),
        asyncio.create_task(run_investment_alert_scheduler()),
    ]
    if settings.MARKET_DATA_ENABLED:
        scheduler_tasks.append(asyncio.create_task(run_market_data_scheduler()))
    yield
    for task in scheduler_tasks:
        task.cancel()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

register_error_handlers(app)

app.add_middleware(CorrelationMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
# Added last so it runs outermost — preflights get answered before anything else
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Mas afuera que CORS: un body gigante se rechaza antes de que corra
# cualquier otra cosa, en vez de gastar trabajo en CORS/rate-limit primero.
app.add_middleware(BodySizeLimitMiddleware)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR.parent / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.middleware("http")
async def theme_middleware(request: Request, call_next):
    response = await call_next(request)

    if "text/html" not in response.headers.get("content-type", ""):
        return response

    # Determine primary color from JWT (no DB query needed)
    primary = _DEFAULT_HEX
    token = request.cookies.get(settings.JWT_COOKIE_NAME)
    if token:
        payload = decode_access_token(token)
        if payload:
            color_key = payload.get("theme", "violet")
            primary = _THEME_COLORS.get(color_key, _DEFAULT_HEX)

    # Read the response body
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk)
    html = b"".join(chunks).decode("utf-8", errors="replace")

    # Replace default accent color with user's chosen color
    if primary != _DEFAULT_HEX:
        html = html.replace(_DEFAULT_HEX, primary)

    # Inject CSS custom property for forward-compatible usage
    css_vars = f"<style>:root{{--color-primary:{primary};}}</style>"
    html = html.replace("</head>", f"{css_vars}</head>", 1)

    headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
    return Response(content=html, media_type="text/html", status_code=response.status_code, headers=headers)


@app.get("/metrics")
async def metrics(request: Request):
    if settings.METRICS_TOKEN:
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        # compare_digest en vez de == para no filtrar el token por timing.
        if not token or not hmac.compare_digest(token, settings.METRICS_TOKEN):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return Response(content=generate_latest(), media_type="text/plain; version=0.0.4")


@app.get("/")
async def root(request: Request):
    if request.cookies.get(settings.JWT_COOKIE_NAME):
        return RedirectResponse(url="/finanzas/", status_code=303)
    return RedirectResponse(url="/auth/login", status_code=303)


app.include_router(health_router)

from app.modules.auth.routes import router as auth_router
from app.modules.auth.api_routes import router as auth_api_router
from app.modules.finanzas.routes import router as finanzas_router
from app.modules.finanzas.cuentas_routes import router as cuentas_router
from app.modules.anotaciones.routes import router as anotaciones_router
from app.modules.anotaciones.export_routes import router as anotaciones_export_router
from app.modules.eventos.routes import router as eventos_router
from app.modules.eventos.export_routes import router as eventos_export_router
from app.modules.metas.routes import router as metas_router
from app.modules.ajustes.routes import router as ajustes_router
from app.api.v1.router import api_router

app.include_router(auth_router)
app.include_router(auth_api_router)
app.include_router(finanzas_router)
app.include_router(cuentas_router)
app.include_router(anotaciones_router)
app.include_router(anotaciones_export_router)
app.include_router(eventos_router)
app.include_router(eventos_export_router)
app.include_router(metas_router)
app.include_router(ajustes_router)
app.include_router(api_router, prefix="/api/v1")

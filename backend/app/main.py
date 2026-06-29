import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import settings
from app.database import engine, AsyncSessionLocal
from app.core.security import decode_access_token
from app.core.error_handlers import register_error_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
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
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

register_error_handlers(app)

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


@app.get("/")
async def root(request: Request):
    if request.cookies.get(settings.JWT_COOKIE_NAME):
        return RedirectResponse(url="/finanzas/", status_code=303)
    return RedirectResponse(url="/auth/login", status_code=303)


@app.get("/health")
async def health():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}


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

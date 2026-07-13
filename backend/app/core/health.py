import logging
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.core.notifier import send_telegram_alert

logger = logging.getLogger(__name__)

health_router = APIRouter()


@health_router.get("/livez")
async def livez():
    return {"status": "alive"}


@health_router.get("/readyz")
async def readyz():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        error_detail = f"database: {e}"
        logger.error("Readiness check failed: %s", error_detail)

        await send_telegram_alert(
            message=(
                f"\U000026A0 LifeOS - Readiness check failed\n"
                f"Timestamp: {datetime.now().isoformat()}\n"
                f"Error: {error_detail}"
            ),
            event_type="readiness_failure",
        )

        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "detail": error_detail},
        )

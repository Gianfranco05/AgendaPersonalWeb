from fastapi import APIRouter

from app.api.v1.finance import router as finance_router
from app.api.v1.notes import router as notes_router
from app.api.v1.events import router as events_router
from app.api.v1.goals import router as goals_router
from app.api.v1.settings import router as settings_router

api_router = APIRouter()

api_router.include_router(finance_router)
api_router.include_router(notes_router)
api_router.include_router(events_router)
api_router.include_router(goals_router)
api_router.include_router(settings_router)

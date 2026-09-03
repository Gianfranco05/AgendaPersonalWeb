from fastapi import APIRouter

from app.api.v1.finance import router as finance_router
from app.api.v1.notes import router as notes_router
from app.api.v1.events import router as events_router
from app.api.v1.goals import router as goals_router
from app.api.v1.settings import router as settings_router
from app.api.v1.fitness import router as fitness_router
from app.api.v1.nutrition import router as nutrition_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.account import router as account_router
from app.modules.billing.api_routes import router as billing_router
from app.modules.modulos.api_routes import router as modules_router
from app.modules.focus.api_routes import router as focus_router
from app.modules.estudio.api_routes import router as study_router
from app.infra.router import router as infra_router

api_router = APIRouter()

api_router.include_router(finance_router)
api_router.include_router(notes_router)
api_router.include_router(events_router)
api_router.include_router(goals_router)
api_router.include_router(settings_router)
api_router.include_router(fitness_router)
api_router.include_router(nutrition_router)
api_router.include_router(tasks_router)
api_router.include_router(account_router)
api_router.include_router(billing_router)
api_router.include_router(modules_router)
api_router.include_router(focus_router)
api_router.include_router(study_router)
api_router.include_router(infra_router)

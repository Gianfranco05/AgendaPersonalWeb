from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.modules.auth.models import User
from app.modules.modulos.service import ModulesService

router = APIRouter(prefix="/modules", tags=["modules"])


class ModuleOut(BaseModel):
    key: str
    label: str
    description: str
    icon: str
    #: Incluida en la app (gratis, no se puede desactivar).
    is_base: bool
    #: La tiene el usuario: base, o comprada.
    owned: bool
    enabled: bool
    #: Tiene precio cargado en Stripe, o sea que ya se puede comprar.
    for_sale: bool


class ToggleModuleRequest(BaseModel):
    enabled: bool


@router.get("", response_model=list[ModuleOut])
async def list_modules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ModulesService(db).list_for_user(str(current_user.id))


@router.put("/{module_key}", response_model=ModuleOut)
async def toggle_module(
    module_key: str,
    body: ToggleModuleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ModulesService(db).set_enabled(str(current_user.id), module_key, body.enabled)

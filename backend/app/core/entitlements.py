"""Gate de acceso a las plantillas que se compran.

Uso en el router de una plantilla paga:

    router = APIRouter(
        prefix="/study",
        dependencies=[Depends(require_module("study"))],
    )

Sin esto, los endpoints de una plantilla paga quedarian abiertos a cualquiera
con una sesion valida: la compra solo cambiaria lo que muestra la app, no lo
que el server deja hacer.
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user
from app.database import get_db
from app.modules.auth.models import User
from app.modules.modulos.service import ModulesService


def require_module(module_key: str):
    async def _require(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        # Sin Stripe configurado (dev, self-hosted) no se le puede cobrar a
        # nadie: bloquear plantillas que el usuario no tiene forma de comprar
        # dejaria la app a medias.
        if not settings.billing_enabled:
            return
        if not await ModulesService(db).user_owns(str(current_user.id), module_key):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Necesitás comprar esta plantilla",
            )

    return _require

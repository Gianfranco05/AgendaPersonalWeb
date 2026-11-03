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


def module_access_bypassed() -> bool:
    """True cuando las plantillas pagas se liberan por no haber cobro.

    Sin proveedor de pago configurado en dev no se le puede cobrar a nadie:
    bloquear plantillas que el usuario no tiene forma de comprar dejaria la app
    a medias. En produccion no: ahi un token de Mercado Pago vacio o mal
    cargado regalaria todas las plantillas pagas, asi que quedan bloqueadas
    hasta que se configure el cobro. Lo comparten `require_module` y el
    buscador, para que los dos usen exactamente la misma regla.
    """
    return not settings.billing_enabled and not settings.is_production


def require_module(module_key: str):
    async def _require(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        if module_access_bypassed():
            return
        if not await ModulesService(db).user_owns(str(current_user.id), module_key):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Necesitás comprar esta plantilla",
            )

    return _require

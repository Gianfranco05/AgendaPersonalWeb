"""Gate de plan para features pagas.

Uso en un endpoint que deba ser solo-Pro:

    @router.get("/reportes", dependencies=[Depends(require_pro)])
    async def reportes(...):
        ...

O, si el endpoint necesita comportarse distinto en vez de bloquear:

    is_pro: bool = Depends(current_user_is_pro)
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user
from app.database import get_db
from app.modules.auth.models import User
from app.modules.billing.service import BillingService


async def current_user_is_pro(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> bool:
    # Sin Stripe configurado (dev, self-hosted) no se le cobra a nadie: no tiene
    # sentido bloquear features que el usuario no tiene forma de pagar.
    if not settings.billing_enabled:
        return True
    return await BillingService(db).user_is_pro(str(current_user.id))


async def require_pro(is_pro: bool = Depends(current_user_is_pro)) -> None:
    if not is_pro:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Esta función requiere el plan Pro",
        )

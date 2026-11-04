import logging
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.modulos.models import EnabledModule, ModulePurchase
from app.modules.modulos.registry import MODULE_BY_KEY, MODULE_REGISTRY, ModuleDef

logger = logging.getLogger(__name__)


def price_id_for(module: ModuleDef) -> Optional[str]:
    """Price ID de Stripe de una plantilla, o None si todavia no esta a la venta."""
    if module.is_base or not module.price_setting:
        return None
    return getattr(settings, module.price_setting, "") or None


def mp_price_for(module: ModuleDef) -> Optional[int]:
    """Precio (centavos) de Mercado Pago de una plantilla, o None si no se vende."""
    if module.is_base or not module.mp_price_setting:
        return None
    price = getattr(settings, module.mp_price_setting, None)
    return price if price and price > 0 else None


def is_for_sale(module: ModuleDef) -> bool:
    """Si la plantilla se puede comprar con el proveedor de pago activo."""
    if settings.BILLING_PROVIDER == "stripe":
        return price_id_for(module) is not None
    return mp_price_for(module) is not None


class ModulesService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def owned_keys(self, user_id: str) -> set[str]:
        result = await self.db.execute(
            select(ModulePurchase.module_key).where(ModulePurchase.user_id == user_id)
        )
        return set(result.scalars().all())

    async def list_for_user(self, user_id: str) -> list[dict]:
        owned = await self.owned_keys(user_id)
        result = await self.db.execute(
            select(EnabledModule).where(EnabledModule.user_id == user_id)
        )
        overrides = {row.module_key: row.enabled for row in result.scalars().all()}

        modules = []
        for m in MODULE_REGISTRY:
            is_owned = m.is_base or m.key in owned
            modules.append(
                {
                    "key": m.key,
                    "label": m.label,
                    "description": m.description,
                    "icon": m.icon,
                    "is_base": m.is_base,
                    "owned": is_owned,
                    # Las base estan siempre activas. Una plantilla comprada
                    # arranca activa: pagar y no verla no tendria sentido.
                    "enabled": True if m.is_base else (is_owned and overrides.get(m.key, True)),
                    "for_sale": is_for_sale(m),
                }
            )
        return modules

    async def searchable_module_keys(self, user_id: str) -> set[str]:
        """Plantillas en las que el buscador puede mirar.

        Las base siempre. Una paga si `require_module` la dejaria pasar
        (comprada, o el bypass de dev sin cobro) Y el usuario no la apagó: una
        plantilla desactivada no se ve en la app, asi que tampoco tiene que
        aparecer en el buscador (el resultado llevaria a una pantalla apagada).
        Esto es mas estricto que `require_module`, que no mira `enabled`.
        """
        from app.core.entitlements import module_access_bypassed

        owned = await self.owned_keys(user_id)
        result = await self.db.execute(
            select(EnabledModule).where(EnabledModule.user_id == user_id)
        )
        overrides = {row.module_key: row.enabled for row in result.scalars().all()}
        bypass = module_access_bypassed()
        keys: set[str] = set()
        for m in MODULE_REGISTRY:
            if m.is_base:
                keys.add(m.key)
            elif (bypass or m.key in owned) and overrides.get(m.key, True):
                keys.add(m.key)
        return keys

    async def set_enabled(self, user_id: str, module_key: str, enabled: bool) -> dict:
        module = MODULE_BY_KEY.get(module_key)
        if module is None:
            raise HTTPException(status_code=404, detail="Plantilla desconocida")
        if module.is_base:
            raise HTTPException(status_code=400, detail="Esta plantilla no se puede desactivar")

        owned = await self.owned_keys(user_id)
        if module_key not in owned:
            # 402: no es un error del cliente ni falta de permisos, falta pagar.
            raise HTTPException(status_code=402, detail="Todavía no compraste esta plantilla")

        result = await self.db.execute(
            select(EnabledModule).where(
                EnabledModule.user_id == user_id, EnabledModule.module_key == module_key
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = EnabledModule(user_id=user_id, module_key=module_key, enabled=enabled)
            self.db.add(row)
        else:
            row.enabled = enabled
        await self.db.commit()

        return {
            "key": module.key,
            "label": module.label,
            "description": module.description,
            "icon": module.icon,
            "is_base": module.is_base,
            "owned": True,
            "enabled": enabled,
            "for_sale": is_for_sale(module),
        }

    async def grant(
        self,
        user_id: str,
        module_key: str,
        amount_paid: Optional[int] = None,
        currency: Optional[str] = None,
        stripe_session_id: Optional[str] = None,
    ) -> bool:
        """Registra la compra de una plantilla. Solo lo llama un webhook.

        Idempotente: Stripe y Mercado Pago reintentan los webhooks, y una
        segunda entrega del mismo evento no tiene que duplicar la compra ni
        fallar.

        stripe_session_id es la referencia de la compra en el proveedor: el id
        de la Checkout Session en Stripe o el id del pago en Mercado Pago.
        """
        if module_key not in MODULE_BY_KEY:
            logger.warning("Compra de una plantilla desconocida: %s", module_key)
            return False

        result = await self.db.execute(
            select(ModulePurchase).where(
                ModulePurchase.user_id == user_id, ModulePurchase.module_key == module_key
            )
        )
        if result.scalar_one_or_none() is not None:
            return False

        self.db.add(
            ModulePurchase(
                user_id=user_id,
                module_key=module_key,
                amount_paid=amount_paid,
                currency=currency,
                stripe_session_id=stripe_session_id,
            )
        )
        try:
            await self.db.commit()
        except IntegrityError:
            # Dos notificaciones del mismo pago llegando a la vez (MP las manda
            # en rafaga, y hay varios workers) pasan las dos el SELECT de
            # arriba y la segunda pega contra uq_module_purchase_user_key. Es
            # un duplicado, no un error: un 500 haria que MP reintente en loop.
            await self.db.rollback()
            return False
        return True

    async def user_owns(self, user_id: str, module_key: str) -> bool:
        module = MODULE_BY_KEY.get(module_key)
        if module is None:
            return False
        if module.is_base:
            return True
        return module_key in await self.owned_keys(user_id)

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.billing.models import Plan, Subscription, SubscriptionStatus

logger = logging.getLogger(__name__)


class BillingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, user_id: str) -> Subscription:
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == str(user_id))
        )
        sub = result.scalar_one_or_none()
        if sub is None:
            sub = Subscription(user_id=str(user_id), plan=Plan.FREE)
            self.db.add(sub)
            await self.db.commit()
            await self.db.refresh(sub)
        return sub

    async def _by_customer(self, customer_id: str) -> Optional[Subscription]:
        result = await self.db.execute(
            select(Subscription).where(Subscription.stripe_customer_id == customer_id)
        )
        return result.scalar_one_or_none()

    async def link_customer(self, user_id: str, customer_id: str) -> Subscription:
        sub = await self.get_or_create(user_id)
        sub.stripe_customer_id = customer_id
        await self.db.commit()
        await self.db.refresh(sub)
        return sub

    async def apply_subscription_event(self, stripe_subscription: dict) -> bool:
        """Sincroniza el estado local con lo que dice Stripe.

        Stripe es la fuente de verdad del estado de pago: nunca se decide el plan
        localmente, solo se copia lo que llega por webhook.
        """
        customer_id = stripe_subscription.get("customer")
        if not customer_id:
            return False

        sub = await self._by_customer(customer_id)
        if sub is None:
            logger.warning(
                "Webhook de Stripe para un customer desconocido: %s", customer_id
            )
            return False

        status = stripe_subscription.get("status")
        sub.status = status
        sub.stripe_subscription_id = stripe_subscription.get("id")

        period_end = stripe_subscription.get("current_period_end")
        sub.current_period_end = (
            datetime.fromtimestamp(period_end, tz=timezone.utc) if period_end else None
        )

        # canceled/unpaid/incomplete_expired vuelven a free; el resto es Pro y el
        # derecho efectivo lo resuelve Subscription.is_pro segun status y periodo.
        terminal = {"canceled", "unpaid", "incomplete_expired"}
        sub.plan = Plan.FREE if status in terminal else Plan.PRO

        await self.db.commit()
        return True

    async def apply_elite_purchase(self, customer_id: str) -> bool:
        """Pago unico de Elite: no hay objeto de suscripcion de Stripe, asi que
        esto se dispara desde checkout.session.completed en vez de un evento
        customer.subscription.*.
        """
        sub = await self._by_customer(customer_id)
        if sub is None:
            logger.warning(
                "Webhook de Stripe (Elite) para un customer desconocido: %s", customer_id
            )
            return False

        sub.plan = Plan.ELITE
        sub.status = SubscriptionStatus.ACTIVE
        sub.current_period_end = None
        await self.db.commit()
        return True

    async def user_is_pro(self, user_id: str) -> bool:
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == str(user_id))
        )
        sub = result.scalar_one_or_none()
        return sub.is_pro if sub else False

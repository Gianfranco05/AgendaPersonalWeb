import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.models import StripeCustomer

logger = logging.getLogger(__name__)


class BillingService:
    """Vinculo con Stripe. Lo que se compro vive en ModulesService."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_customer_id(self, user_id: str) -> Optional[str]:
        result = await self.db.execute(
            select(StripeCustomer).where(StripeCustomer.user_id == str(user_id))
        )
        row = result.scalar_one_or_none()
        return row.stripe_customer_id if row else None

    async def link_customer(self, user_id: str, customer_id: str) -> str:
        result = await self.db.execute(
            select(StripeCustomer).where(StripeCustomer.user_id == str(user_id))
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = StripeCustomer(user_id=str(user_id), stripe_customer_id=customer_id)
            self.db.add(row)
        else:
            row.stripe_customer_id = customer_id
        await self.db.commit()
        return customer_id

    async def user_id_for_customer(self, customer_id: str) -> Optional[str]:
        result = await self.db.execute(
            select(StripeCustomer).where(StripeCustomer.stripe_customer_id == customer_id)
        )
        row = result.scalar_one_or_none()
        return row.user_id if row else None

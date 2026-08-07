from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class Plan:
    FREE = "free"
    PRO = "pro"


class SubscriptionStatus:
    """Espejo de los estados de Stripe que nos importan."""

    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"


# Estados en los que el usuario todavia tiene derecho a las features Pro.
# past_due entra a proposito: Stripe reintenta el cobro varios dias y cortarle
# el acceso al primer fallo de tarjeta es la forma mas rapida de perder clientes.
ENTITLED_STATUSES = frozenset(
    {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING, SubscriptionStatus.PAST_DUE}
)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True, index=True
    )
    plan: Mapped[str] = mapped_column(String(20), default=Plan.FREE)
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def is_pro(self) -> bool:
        if self.plan != Plan.PRO or self.status not in ENTITLED_STATUSES:
            return False
        if self.current_period_end is None:
            return True
        # El webhook puede no llegar (Stripe caido, deploy en el medio): si el
        # periodo ya vencio no se sigue regalando Pro por inercia.
        period_end = self.current_period_end
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=timezone.utc)
        return period_end > datetime.now(timezone.utc)

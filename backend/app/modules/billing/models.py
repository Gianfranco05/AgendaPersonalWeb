from uuid import uuid4
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class StripeCustomer(Base):
    """Vinculo 1:1 entre un usuario y su customer de Stripe.

    No hay suscripciones: lo que se vende son plantillas sueltas, de pago
    unico (ver modulos/models.py::ModulePurchase). Igual hace falta un customer
    para que las compras queden agrupadas bajo la misma persona en Stripe y
    para poder emitir un reembolso despues.
    """

    __tablename__ = "stripe_customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True, index=True
    )
    stripe_customer_id: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

from uuid import uuid4
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class ModulePurchase(Base):
    """Compra unica de una plantilla: no vence y no se renueva.

    Es la fuente de verdad de "esta plantilla es mia". Se crea solo desde el
    webhook de Stripe (checkout.session.completed), nunca desde el cliente.
    Se guarda el importe pagado porque el precio de la plantilla puede cambiar
    despues, y el comprobante tiene que reflejar lo que la persona pago.
    """

    __tablename__ = "module_purchases"
    __table_args__ = (
        UniqueConstraint("user_id", "module_key", name="uq_module_purchase_user_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    module_key: Mapped[str] = mapped_column(String(50))
    #: En la unidad minima de la moneda (centavos), como lo devuelve Stripe.
    amount_paid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    stripe_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EnabledModule(Base):
    """Override de un usuario sobre una plantilla no-base (on/off).

    Separado de la compra a proposito: comprar una plantilla no obliga a
    tenerla siempre visible, y apagarla no la devuelve ni borra sus datos.
    Ausencia de fila = no habilitada. Las base ni se consultan aca: siempre
    estan activas (ver ModulesService.list_for_user).
    """

    __tablename__ = "enabled_modules"
    __table_args__ = (UniqueConstraint("user_id", "module_key", name="uq_enabled_module_user_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    module_key: Mapped[str] = mapped_column(String(50))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

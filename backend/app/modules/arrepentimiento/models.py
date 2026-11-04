from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WithdrawalRequest(Base):
    """Solicitud del "Botón de arrepentimiento" (Res. 424/2020, Ley 24.240 art. 34).

    Es un registro legal, no un dato de uso de la app: la persona lo carga sin
    cuenta, y tiene que quedar constancia aunque despues borre su cuenta. Por
    eso `user_id` es opcional y, al borrar la cuenta, se desvincula en vez de
    borrar la fila (ver cuenta/service.py::RETAINED_TABLES).
    """

    __tablename__ = "withdrawal_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    #: Codigo de tramite que se le da a la persona (ARR-XXXXXX).
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), index=True)
    #: Texto libre: plantilla, fecha y numero de operacion de Mercado Pago.
    purchase_detail: Mapped[str] = mapped_column(Text)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    #: Solo si el pedido llego con una sesion valida. Nunca es requisito.
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    #: La compra conocida es mas vieja que el plazo de la politica de
    #: reembolsos (14 dias). No bloquea el pedido: marca que hay que revisarlo
    #: a mano antes de responder.
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

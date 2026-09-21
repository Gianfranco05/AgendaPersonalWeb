from uuid import uuid4
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class PushToken(Base):
    """Un push token de Expo por dispositivo.

    Unico en `token` (no en `user_id`): un usuario puede tener varios
    dispositivos, y reasignar el token a otro usuario en `register` (upsert)
    es justamente lo que evita que un logout/login de otra cuenta en el mismo
    telefono le siga mandando notificaciones a la cuenta vieja.
    """

    __tablename__ = "push_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    device_info: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

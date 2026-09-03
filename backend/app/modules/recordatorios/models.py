from uuid import uuid4
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class Reminder(Base):
    """Un recordatorio local: el server solo guarda la configuracion (para
    que sobreviva una reinstalacion y se sincronice entre dispositivos), la
    notificacion en si la programa el celular con expo-notifications — este
    modelo no dispara nada.
    """

    __tablename__ = "reminders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    message: Mapped[str] = mapped_column(String(200))
    #: Emoji corto (no hay libreria de iconos vectorial en el proyecto — ver
    #: Goal.icon/Category.icon, mismo patron). Se antepone al mensaje en la
    #: notificacion; Android no permite un icono nativo distinto por item de
    #: notificacion sin assets nativos custom por app, no por recordatorio.
    icon: Mapped[str] = mapped_column(String(8), default="🔔")
    hour: Mapped[int] = mapped_column(Integer)
    minute: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

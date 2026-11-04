from uuid import uuid4
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class Reminder(Base):
    """Un recordatorio: el disparo real puede venir de dos lados.

    Si el dispositivo tiene un push token registrado (ver modulo `push`), lo
    dispara el scheduler del servidor via Expo Push. Si no (Expo Go en
    Android, sin projectId de EAS, permiso denegado), el celular lo programa
    localmente con expo-notifications como antes — el server solo guarda la
    configuracion para que sobreviva una reinstalacion y se sincronice entre
    dispositivos, pero en ese caso no dispara nada.
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
    #: Minutos al este de UTC (mismo signo que `tz_offset_minutes` en
    #: focus/api_routes.py). None = el cliente todavia no lo mando (clientes
    #: viejos, o un recordatorio creado offline): el scheduler del servidor
    #: ignora ese recordatorio y queda solo la programacion local del
    #: dispositivo. Se pisa en cada create/update, asi que un cambio de huso
    #: horario (viaje) o de DST se corrige solo la proxima vez que el usuario
    #: toque el recordatorio — no hay reconciliacion automatica en segundo
    #: plano por ahora.
    timezone_offset_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

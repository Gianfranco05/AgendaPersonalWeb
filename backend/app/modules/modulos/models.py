from uuid import uuid4
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class EnabledModule(Base):
    """Override de un usuario sobre un modulo no-base (on/off).

    Ausencia de fila = no habilitado. Los modulos base ni siquiera se
    consultan aca: siempre estan activos (ver ModulesService.list_for_user).
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

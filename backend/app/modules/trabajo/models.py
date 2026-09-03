from uuid import uuid4
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Float, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class OpportunityStatus:
    APLICADO = "aplicado"
    ENTREVISTA = "entrevista"
    OFERTA = "oferta"
    RECHAZADO = "rechazado"
    ACEPTADO = "aceptado"


OPPORTUNITY_STATUSES = frozenset(
    {
        OpportunityStatus.APLICADO,
        OpportunityStatus.ENTREVISTA,
        OpportunityStatus.OFERTA,
        OpportunityStatus.RECHAZADO,
        OpportunityStatus.ACEPTADO,
    }
)

# Estados donde la oportunidad ya se cerro, para no seguir contandola como
# "activa" en el resumen.
TERMINAL_STATUSES = frozenset({OpportunityStatus.RECHAZADO, OpportunityStatus.ACEPTADO})


class WorkOpportunity(Base):
    """Un puesto en el pipeline de busqueda laboral: no es una tarea suelta,
    es la carrera profesional vista como proceso con etapas."""

    __tablename__ = "work_opportunities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    company: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(20), default=OpportunityStatus.APLICADO, index=True)
    salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    applied_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

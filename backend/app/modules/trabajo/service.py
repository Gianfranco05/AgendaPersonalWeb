from typing import Optional

from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud_service import apply_changes, get_by_id_or_404
from app.modules.trabajo.models import (
    OPPORTUNITY_STATUSES,
    TERMINAL_STATUSES,
    OpportunityStatus,
    WorkOpportunity,
)


class WorkService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _validate_status(self, status: Optional[str]) -> None:
        if status is not None and status not in OPPORTUNITY_STATUSES:
            raise HTTPException(status_code=422, detail="Estado inválido")

    async def list_opportunities(self, user_id: str, status: Optional[str] = None) -> list[WorkOpportunity]:
        self._validate_status(status)
        query = select(WorkOpportunity).where(WorkOpportunity.user_id == user_id)
        if status:
            query = query.where(WorkOpportunity.status == status)
        result = await self.db.execute(query.order_by(WorkOpportunity.updated_at.desc()))
        return list(result.scalars().all())

    async def _get(self, user_id: str, opportunity_id: str) -> WorkOpportunity:
        return await get_by_id_or_404(
            self.db, WorkOpportunity, opportunity_id, user_id, not_found_detail="No encontrado"
        )

    async def create_opportunity(
        self,
        user_id: str,
        company: str,
        role: str,
        status: Optional[str] = None,
        salary: Optional[float] = None,
        applied_date=None,
        notes: Optional[str] = None,
    ) -> WorkOpportunity:
        self._validate_status(status)
        opp = WorkOpportunity(
            user_id=user_id,
            company=company,
            role=role,
            status=status or OpportunityStatus.APLICADO,
            salary=salary,
            applied_date=applied_date,
            notes=notes or None,
        )
        self.db.add(opp)
        await self.db.commit()
        await self.db.refresh(opp)
        return opp

    async def update_opportunity(self, user_id: str, opportunity_id: str, changes: dict) -> WorkOpportunity:
        opp = await self._get(user_id, opportunity_id)
        self._validate_status(changes.get("status"))
        apply_changes(opp, changes)
        await self.db.commit()
        await self.db.refresh(opp)
        return opp

    async def delete_opportunity(self, user_id: str, opportunity_id: str) -> None:
        opp = await self._get(user_id, opportunity_id)
        await self.db.delete(opp)
        await self.db.commit()

    async def summary(self, user_id: str) -> dict:
        result = await self.db.execute(
            select(
                func.count(WorkOpportunity.id),
                func.sum(case((WorkOpportunity.status.notin_(TERMINAL_STATUSES), 1), else_=0)),
                func.sum(case((WorkOpportunity.status == OpportunityStatus.ENTREVISTA, 1), else_=0)),
                func.sum(case((WorkOpportunity.status == OpportunityStatus.OFERTA, 1), else_=0)),
                func.sum(case((WorkOpportunity.status == OpportunityStatus.ACEPTADO, 1), else_=0)),
            ).where(WorkOpportunity.user_id == user_id)
        )
        total, active, entrevista, oferta, aceptado = result.one()

        return {
            "total": total or 0,
            "active": active or 0,
            "entrevista": entrevista or 0,
            "oferta": oferta or 0,
            "aceptado": aceptado or 0,
        }

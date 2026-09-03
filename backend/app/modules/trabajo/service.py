from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
        result = await self.db.execute(
            select(WorkOpportunity).where(
                WorkOpportunity.id == opportunity_id, WorkOpportunity.user_id == user_id
            )
        )
        opp = result.scalar_one_or_none()
        if opp is None:
            raise HTTPException(status_code=404, detail="No encontrado")
        return opp

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
        for field, value in changes.items():
            if value is not None:
                setattr(opp, field, value)
        await self.db.commit()
        await self.db.refresh(opp)
        return opp

    async def delete_opportunity(self, user_id: str, opportunity_id: str) -> None:
        opp = await self._get(user_id, opportunity_id)
        await self.db.delete(opp)
        await self.db.commit()

    async def summary(self, user_id: str) -> dict:
        opportunities = await self.list_opportunities(user_id)
        active = [o for o in opportunities if o.status not in TERMINAL_STATUSES]

        return {
            "total": len(opportunities),
            "active": len(active),
            "entrevista": sum(1 for o in opportunities if o.status == OpportunityStatus.ENTREVISTA),
            "oferta": sum(1 for o in opportunities if o.status == OpportunityStatus.OFERTA),
            "aceptado": sum(1 for o in opportunities if o.status == OpportunityStatus.ACEPTADO),
        }

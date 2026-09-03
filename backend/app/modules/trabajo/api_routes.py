from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.entitlements import require_module
from app.database import get_db
from app.modules.auth.models import User
from app.modules.trabajo.service import WorkService

# Plantilla de pago: sin la compra, el server no deja tocar estos endpoints.
router = APIRouter(
    prefix="/work", tags=["work"], dependencies=[Depends(require_module("work"))]
)


class OpportunityOut(BaseModel):
    id: str
    company: str
    role: str
    status: str
    salary: Optional[float] = None
    applied_date: Optional[date] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class OpportunityCreate(BaseModel):
    company: str = Field(min_length=1, max_length=160)
    role: str = Field(min_length=1, max_length=160)
    status: Optional[str] = None
    salary: Optional[float] = Field(default=None, ge=0)
    applied_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class OpportunityUpdate(BaseModel):
    company: Optional[str] = Field(default=None, min_length=1, max_length=160)
    role: Optional[str] = Field(default=None, min_length=1, max_length=160)
    status: Optional[str] = None
    salary: Optional[float] = Field(default=None, ge=0)
    applied_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class WorkSummaryOut(BaseModel):
    total: int
    active: int
    entrevista: int
    oferta: int
    aceptado: int


@router.get("/opportunities", response_model=list[OpportunityOut])
async def list_opportunities(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await WorkService(db).list_opportunities(str(current_user.id), status_filter)


@router.post("/opportunities", response_model=OpportunityOut, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    body: OpportunityCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await WorkService(db).create_opportunity(
        str(current_user.id),
        body.company,
        body.role,
        body.status,
        body.salary,
        body.applied_date,
        body.notes,
    )


@router.patch("/opportunities/{opportunity_id}", response_model=OpportunityOut)
async def update_opportunity(
    opportunity_id: str,
    body: OpportunityUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await WorkService(db).update_opportunity(
        str(current_user.id), opportunity_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/opportunities/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_opportunity(
    opportunity_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await WorkService(db).delete_opportunity(str(current_user.id), opportunity_id)


@router.get("/summary", response_model=WorkSummaryOut)
async def get_work_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await WorkService(db).summary(str(current_user.id))

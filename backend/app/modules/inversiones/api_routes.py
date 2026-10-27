from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today
from app.core.dependencies import get_current_user
from app.database import get_db
from app.modules.auth.models import User
from app.modules.inversiones.schemas import (
    AssetType,
    InvestmentCreate,
    InvestmentOut,
    InvestmentSummary,
    InvestmentUpdate,
    NetWorthOut,
    RenewalChainOut,
    RenewFixedTermIn,
    RenewOut,
)
from app.modules.inversiones.service import InvestmentService, to_out

# Parte de Finanzas (plantilla base): sin `require_module`, solo autenticacion.
router = APIRouter(prefix="/finance", tags=["finance"])

TzOffset = Query(0, ge=-840, le=840, description="Minutos al este de UTC (Buenos Aires = -180)")


@router.get("/investments", response_model=list[InvestmentOut])
async def list_investments(
    status_filter: Literal["active", "closed", "all"] = Query("active", alias="status"),
    asset_type: Optional[AssetType] = None,
    tz_offset_minutes: int = TzOffset,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = InvestmentService(db)
    items = await service.list(
        current_user.id, status_filter, asset_type.value if asset_type else None
    )
    today = local_today(tz_offset_minutes)
    series = await service.inflation_series()
    renewed = await service.renewal_map(current_user.id)
    return [to_out(inv, today, series, renewed.get(inv.id)) for inv in items]


# Declarada antes de `/investments/{id}`: si no, "summary" se leeria como un id.
@router.get("/investments/summary", response_model=InvestmentSummary)
async def investments_summary(
    tz_offset_minutes: int = TzOffset,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await InvestmentService(db).summary(current_user.id, local_today(tz_offset_minutes))


@router.get("/investments/{investment_id}", response_model=InvestmentOut)
async def get_investment(
    investment_id: str,
    tz_offset_minutes: int = TzOffset,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = InvestmentService(db)
    investment = await service.get(investment_id, current_user.id)
    if not investment:
        raise HTTPException(status_code=404, detail="Inversión no encontrada")
    renewed = await service.renewal_map(current_user.id)
    return to_out(
        investment,
        local_today(tz_offset_minutes),
        await service.inflation_series(),
        renewed.get(investment.id),
    )


@router.post("/investments", response_model=InvestmentOut, status_code=status.HTTP_201_CREATED)
async def create_investment(
    data: InvestmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = InvestmentService(db)
    investment = await service.create(current_user.id, data)
    # Sin tz del cliente en el POST, el devengado se calcula con el offset que
    # el cliente guardo en el activo (o el de Argentina si no mando ninguno).
    offset = investment.timezone_offset_minutes if investment.timezone_offset_minutes is not None else -180
    return to_out(investment, local_today(offset), await service.inflation_series())


@router.put("/investments/{investment_id}", response_model=InvestmentOut)
async def update_investment(
    investment_id: str,
    data: InvestmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = InvestmentService(db)
    investment = await service.get(investment_id, current_user.id)
    if not investment:
        raise HTTPException(status_code=404, detail="Inversión no encontrada")
    updated = await service.update(investment, data)
    offset = updated.timezone_offset_minutes if updated.timezone_offset_minutes is not None else -180
    renewed = await service.renewal_map(current_user.id)
    return to_out(
        updated, local_today(offset), await service.inflation_series(), renewed.get(updated.id)
    )


@router.post("/investments/{investment_id}/renew", response_model=RenewOut)
async def renew_investment(
    investment_id: str,
    data: RenewFixedTermIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = InvestmentService(db)
    investment = await service.get(investment_id, current_user.id)
    if not investment:
        raise HTTPException(status_code=404, detail="Inversión no encontrada")
    closed, renewed, interest_transaction_id = await service.renew(investment, data)
    offset = (
        data.timezone_offset_minutes
        if data.timezone_offset_minutes is not None
        else renewed.timezone_offset_minutes
        if renewed.timezone_offset_minutes is not None
        else -180
    )
    today = local_today(offset)
    series = await service.inflation_series()
    return RenewOut(
        closed=to_out(closed, today, series, renewed.id),
        renewed=to_out(renewed, today, series, None),
        interest_transaction_id=interest_transaction_id,
    )


@router.get("/investments/{investment_id}/renewals", response_model=RenewalChainOut)
async def investment_renewals(
    investment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = InvestmentService(db)
    investment = await service.get(investment_id, current_user.id)
    if not investment:
        raise HTTPException(status_code=404, detail="Inversión no encontrada")
    return await service.renewals(investment)


@router.delete("/investments/{investment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_investment(
    investment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = InvestmentService(db)
    investment = await service.get(investment_id, current_user.id)
    if not investment:
        raise HTTPException(status_code=404, detail="Inversión no encontrada")
    await service.delete(investment)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/net-worth", response_model=NetWorthOut)
async def get_net_worth(
    tz_offset_minutes: int = TzOffset,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await InvestmentService(db).net_worth(current_user.id, local_today(tz_offset_minutes))

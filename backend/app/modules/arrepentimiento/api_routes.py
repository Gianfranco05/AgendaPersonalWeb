from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_optional
from app.core.http_security import rate_limit_withdrawal
from app.database import get_db
from app.modules.arrepentimiento.service import WithdrawalService

# Publico a proposito: la Res. 424/2020 exige que se pueda usar sin cuenta ni
# login. El usuario logueado, si lo hay, solo se vincula al pedido.
router = APIRouter(prefix="/arrepentimiento", tags=["arrepentimiento"])


class WithdrawalIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    purchase_detail: str = Field(min_length=1, max_length=1000)
    message: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("full_name", "purchase_detail", mode="before")
    @classmethod
    def _strip_required(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("message", mode="before")
    @classmethod
    def _strip_optional(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value


class WithdrawalOut(BaseModel):
    code: str
    created_at: datetime


@router.post(
    "",
    response_model=WithdrawalOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_withdrawal)],
)
async def create_withdrawal_request(
    body: WithdrawalIn,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    request = await WithdrawalService(db).create(
        full_name=body.full_name,
        email=str(body.email),
        purchase_detail=body.purchase_detail,
        message=body.message,
        user_id=str(current_user.id) if current_user else None,
    )
    return WithdrawalOut(code=request.code, created_at=request.created_at)

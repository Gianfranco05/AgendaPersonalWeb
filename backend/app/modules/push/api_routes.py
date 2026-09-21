from typing import Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.modules.auth.models import User
from app.modules.push.service import PushService

router = APIRouter(prefix="/push", tags=["push"])


class PushTokenIn(BaseModel):
    token: str = Field(min_length=1, max_length=255)
    device_info: Optional[str] = Field(default=None, max_length=255)


@router.post("/register", status_code=status.HTTP_204_NO_CONTENT)
async def register_push_token(
    body: PushTokenIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await PushService(db).register(str(current_user.id), body.token, body.device_info)


@router.delete("/register", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_push_token(
    body: PushTokenIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await PushService(db).unregister(body.token)

from typing import Type, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


async def get_owned_or_404(
    db: AsyncSession,
    model: Type[ModelT],
    obj_id: str,
    user_id: str,
    detail: str = "No encontrado",
) -> ModelT:
    # user_id is the tenant boundary (1 tenant = 1 user) — always filter by it, never just id.
    result = await db.execute(
        select(model).where(model.id == obj_id, model.user_id == user_id)
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return obj

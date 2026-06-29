from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ajustes.models import UserPreference


class UserPreferenceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user(self, user_id: str) -> Optional[UserPreference]:
        result = await self.db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, user_id: str, data: dict) -> UserPreference:
        prefs = await self.get_by_user(user_id)
        if prefs is None:
            prefs = UserPreference(user_id=user_id, **data)
            self.db.add(prefs)
        else:
            for key, value in data.items():
                setattr(prefs, key, value)
        await self.db.commit()
        await self.db.refresh(prefs)
        return prefs

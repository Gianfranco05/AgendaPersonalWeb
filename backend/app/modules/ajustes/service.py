from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ajustes.models import UserPreference
from app.modules.ajustes.repository import UserPreferenceRepository
from app.modules.ajustes.schemas import UserPreferenceUpdate


class SettingsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserPreferenceRepository(db)

    async def get_preferences(self, user_id: str) -> UserPreference:
        prefs = await self.repo.get_by_user(user_id)
        if prefs is None:
            prefs = await self.repo.upsert(user_id, {})
        return prefs

    async def update_preferences(
        self, user_id: str, data: UserPreferenceUpdate
    ) -> UserPreference:
        update_data = data.model_dump(exclude_unset=True)
        return await self.repo.upsert(user_id, update_data)

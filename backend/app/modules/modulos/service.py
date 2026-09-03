from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modulos.models import EnabledModule
from app.modules.modulos.registry import MODULE_BY_KEY, MODULE_REGISTRY


class ModulesService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(self, user_id: str) -> list[dict]:
        result = await self.db.execute(
            select(EnabledModule).where(EnabledModule.user_id == user_id)
        )
        overrides = {row.module_key: row.enabled for row in result.scalars().all()}

        return [
            {
                "key": m.key,
                "label": m.label,
                "description": m.description,
                "icon": m.icon,
                "is_base": m.is_base,
                # Los base siempre estan activos; los nuevos arrancan apagados
                # hasta que el usuario los prenda.
                "enabled": True if m.is_base else overrides.get(m.key, False),
            }
            for m in MODULE_REGISTRY
        ]

    async def set_enabled(self, user_id: str, module_key: str, enabled: bool) -> dict:
        module_def = MODULE_BY_KEY.get(module_key)
        if module_def is None:
            raise HTTPException(status_code=404, detail="Módulo desconocido")
        if module_def.is_base:
            raise HTTPException(status_code=400, detail="Este módulo no se puede desactivar")

        result = await self.db.execute(
            select(EnabledModule).where(
                EnabledModule.user_id == user_id, EnabledModule.module_key == module_key
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = EnabledModule(user_id=user_id, module_key=module_key, enabled=enabled)
            self.db.add(row)
        else:
            row.enabled = enabled
        await self.db.commit()

        return {
            "key": module_def.key,
            "label": module_def.label,
            "description": module_def.description,
            "icon": module_def.icon,
            "is_base": module_def.is_base,
            "enabled": enabled,
        }

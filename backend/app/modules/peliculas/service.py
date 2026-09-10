from typing import Optional

from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud_service import apply_changes, get_by_id_or_404
from app.modules.peliculas.models import MEDIA_STATUSES, MEDIA_TYPES, MediaItem, MediaStatus, MediaType


class MediaService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _validate_status(self, status: Optional[str]) -> None:
        if status is not None and status not in MEDIA_STATUSES:
            raise HTTPException(status_code=422, detail="Estado inválido")

    def _validate_type(self, media_type: Optional[str]) -> None:
        if media_type is not None and media_type not in MEDIA_TYPES:
            raise HTTPException(status_code=422, detail="Tipo inválido: pelicula o serie")

    async def list_items(
        self, user_id: str, status: Optional[str] = None, media_type: Optional[str] = None
    ) -> list[MediaItem]:
        self._validate_status(status)
        self._validate_type(media_type)
        query = select(MediaItem).where(MediaItem.user_id == user_id)
        if status:
            query = query.where(MediaItem.status == status)
        if media_type:
            query = query.where(MediaItem.media_type == media_type)
        result = await self.db.execute(query.order_by(MediaItem.updated_at.desc()))
        return list(result.scalars().all())

    async def _get_item(self, user_id: str, item_id: str) -> MediaItem:
        return await get_by_id_or_404(
            self.db, MediaItem, item_id, user_id, not_found_detail="No encontrado"
        )

    async def create_item(
        self,
        user_id: str,
        title: str,
        media_type: Optional[str] = None,
        status: Optional[str] = None,
        rating: Optional[float] = None,
        year: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> MediaItem:
        self._validate_type(media_type)
        self._validate_status(status)
        item = MediaItem(
            user_id=user_id,
            title=title,
            media_type=media_type or MediaType.PELICULA,
            status=status or MediaStatus.PENDIENTE,
            rating=rating,
            year=year,
            notes=notes or None,
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def update_item(self, user_id: str, item_id: str, changes: dict) -> MediaItem:
        item = await self._get_item(user_id, item_id)
        self._validate_status(changes.get("status"))
        self._validate_type(changes.get("media_type"))
        apply_changes(item, changes)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_item(self, user_id: str, item_id: str) -> None:
        item = await self._get_item(user_id, item_id)
        await self.db.delete(item)
        await self.db.commit()

    async def summary(self, user_id: str) -> dict:
        result = await self.db.execute(
            select(
                func.count(MediaItem.id),
                func.sum(case((MediaItem.status == MediaStatus.PENDIENTE, 1), else_=0)),
                func.sum(case((MediaItem.status == MediaStatus.VIENDO, 1), else_=0)),
                func.sum(case((MediaItem.status == MediaStatus.VISTO, 1), else_=0)),
                func.avg(case((MediaItem.status == MediaStatus.VISTO, MediaItem.rating), else_=None)),
            ).where(MediaItem.user_id == user_id)
        )
        total, pendientes, viendo, vistos, average_rating = result.one()

        return {
            "total": total or 0,
            "pendientes": pendientes or 0,
            "viendo": viendo or 0,
            "vistos": vistos or 0,
            "average_rating": round(average_rating, 1) if average_rating is not None else None,
        }

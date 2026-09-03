from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
        result = await self.db.execute(
            select(MediaItem).where(MediaItem.id == item_id, MediaItem.user_id == user_id)
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise HTTPException(status_code=404, detail="No encontrado")
        return item

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
        for field, value in changes.items():
            if value is not None:
                setattr(item, field, value)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_item(self, user_id: str, item_id: str) -> None:
        item = await self._get_item(user_id, item_id)
        await self.db.delete(item)
        await self.db.commit()

    async def summary(self, user_id: str) -> dict:
        items = await self.list_items(user_id)
        vistos = [i for i in items if i.status == MediaStatus.VISTO]
        rated = [i.rating for i in vistos if i.rating is not None]

        return {
            "total": len(items),
            "pendientes": sum(1 for i in items if i.status == MediaStatus.PENDIENTE),
            "viendo": sum(1 for i in items if i.status == MediaStatus.VIENDO),
            "vistos": len(vistos),
            "average_rating": round(sum(rated) / len(rated), 1) if rated else None,
        }

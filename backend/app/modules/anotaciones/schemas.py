from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class NoteBase(BaseModel):
    title: str
    content: str
    color: str = "#ffffff"
    is_pinned: bool = False


class NoteCreate(NoteBase):
    tag_names: list[str] = []


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    color: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None
    # None = no tocar los tags; [] = sacarlos todos. Reemplaza la lista
    # completa (no suma): el cliente manda el estado final que quiere.
    tag_names: Optional[list[str]] = None


class NoteResponse(NoteBase):
    id: UUID
    user_id: UUID
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TagBase(BaseModel):
    name: str
    color: str = "#6366f1"


class TagCreate(TagBase):
    pass


class TagResponse(TagBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.entitlements import require_module
from app.database import get_db
from app.modules.auth.models import User
from app.modules.biblioteca.service import LibraryService

# Plantilla de pago: sin la compra, el server no deja tocar estos endpoints.
router = APIRouter(
    prefix="/library", tags=["library"], dependencies=[Depends(require_module("library"))]
)


class BookOut(BaseModel):
    id: str
    title: str
    author: Optional[str] = None
    status: str
    rating: Optional[float] = None
    pages: Optional[int] = None
    notes: Optional[str] = None
    started_date: Optional[date] = None
    finished_date: Optional[date] = None

    model_config = {"from_attributes": True}


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: Optional[str] = Field(default=None, max_length=200)
    status: Optional[str] = None
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    pages: Optional[int] = Field(default=None, ge=1)
    notes: Optional[str] = Field(default=None, max_length=1000)


class BookUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    author: Optional[str] = Field(default=None, max_length=200)
    status: Optional[str] = None
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    pages: Optional[int] = Field(default=None, ge=1)
    notes: Optional[str] = Field(default=None, max_length=1000)
    started_date: Optional[date] = None
    finished_date: Optional[date] = None


class LibrarySummaryOut(BaseModel):
    total: int
    pendientes: int
    leyendo: int
    leidos: int
    average_rating: Optional[float] = None


@router.get("/books", response_model=list[BookOut])
async def list_books(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LibraryService(db).list_books(str(current_user.id), status_filter)


@router.post("/books", response_model=BookOut, status_code=status.HTTP_201_CREATED)
async def create_book(
    body: BookCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LibraryService(db).create_book(
        str(current_user.id), body.title, body.author, body.status, body.rating, body.pages, body.notes
    )


@router.patch("/books/{book_id}", response_model=BookOut)
async def update_book(
    book_id: str,
    body: BookUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LibraryService(db).update_book(
        str(current_user.id), book_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await LibraryService(db).delete_book(str(current_user.id), book_id)


@router.get("/summary", response_model=LibrarySummaryOut)
async def get_library_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LibraryService(db).summary(str(current_user.id))

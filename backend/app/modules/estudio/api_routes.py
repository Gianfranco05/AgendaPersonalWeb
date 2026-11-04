from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.entitlements import require_module
from app.database import get_db
from app.modules.auth.models import User
from app.modules.estudio.service import StudyService

# Plantilla de pago: sin la compra, el server no deja tocar estos endpoints.
router = APIRouter(
    prefix="/study", tags=["study"], dependencies=[Depends(require_module("study"))]
)


# ── Schemas ──────────────────────────────────────────────────────────────────

class SubjectOut(BaseModel):
    id: str
    name: str
    professor: Optional[str] = None
    color: str
    status: str

    model_config = {"from_attributes": True}


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    professor: Optional[str] = Field(default=None, max_length=120)
    color: Optional[str] = Field(default=None, max_length=9)
    status: Optional[str] = None


class SubjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    professor: Optional[str] = Field(default=None, max_length=120)
    color: Optional[str] = Field(default=None, max_length=9)
    status: Optional[str] = None


class ExamOut(BaseModel):
    id: str
    subject_id: str
    title: str
    exam_date: date
    grade: Optional[float] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class ExamCreate(BaseModel):
    subject_id: str
    title: str = Field(min_length=1, max_length=160)
    exam_date: date
    grade: Optional[float] = Field(default=None, ge=0, le=10)
    notes: Optional[str] = Field(default=None, max_length=500)


class ExamUpdate(BaseModel):
    subject_id: Optional[str] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=160)
    exam_date: Optional[date] = None
    grade: Optional[float] = Field(default=None, ge=0, le=10)
    notes: Optional[str] = Field(default=None, max_length=500)


class StudySummaryOut(BaseModel):
    subjects_total: int
    subjects_cursando: int
    subjects_aprobadas: int
    average_grade: Optional[float] = None
    next_exam: Optional[ExamOut] = None
    upcoming_count: int


# ── Materias ─────────────────────────────────────────────────────────────────

@router.get("/subjects", response_model=list[SubjectOut])
async def list_subjects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await StudyService(db).list_subjects(str(current_user.id))


@router.post("/subjects", response_model=SubjectOut, status_code=status.HTTP_201_CREATED)
async def create_subject(
    body: SubjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await StudyService(db).create_subject(
        str(current_user.id), body.name, body.professor, body.color, body.status
    )


@router.patch("/subjects/{subject_id}", response_model=SubjectOut)
async def update_subject(
    subject_id: str,
    body: SubjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await StudyService(db).update_subject(
        str(current_user.id), subject_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject(
    subject_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await StudyService(db).delete_subject(str(current_user.id), subject_id)


# ── Examenes ─────────────────────────────────────────────────────────────────

@router.get("/exams", response_model=list[ExamOut])
async def list_exams(
    upcoming: bool = Query(False),
    # Minutos al este de UTC (Buenos Aires = -180). Opcional: sin el, "hoy" es
    # el del server (UTC) y cambia a las 21:00 en Argentina.
    tz_offset_minutes: Optional[int] = Query(None, ge=-840, le=840),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await StudyService(db).list_exams(str(current_user.id), upcoming, tz_offset_minutes)


@router.post("/exams", response_model=ExamOut, status_code=status.HTTP_201_CREATED)
async def create_exam(
    body: ExamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await StudyService(db).create_exam(
        str(current_user.id),
        body.subject_id,
        body.title,
        body.exam_date,
        body.grade,
        body.notes,
    )


@router.patch("/exams/{exam_id}", response_model=ExamOut)
async def update_exam(
    exam_id: str,
    body: ExamUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await StudyService(db).update_exam(
        str(current_user.id), exam_id, body.model_dump(exclude_unset=True)
    )


@router.delete("/exams/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exam(
    exam_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await StudyService(db).delete_exam(str(current_user.id), exam_id)


@router.get("/summary", response_model=StudySummaryOut)
async def get_study_summary(
    # Minutos al este de UTC (Buenos Aires = -180). Opcional: sin el, "hoy" es
    # el del server (UTC) y cambia a las 21:00 en Argentina.
    tz_offset_minutes: Optional[int] = Query(None, ge=-840, le=840),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await StudyService(db).summary(str(current_user.id), tz_offset_minutes)

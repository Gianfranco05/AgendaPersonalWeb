import unicodedata
from datetime import date
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today
from app.core.crud_service import apply_changes, get_by_id_or_404
from app.modules.estudio.models import SUBJECT_STATUSES, Exam, Subject, SubjectStatus


def _alphabetical_key(name: str) -> str:
    """Clave de orden que ignora acentos y mayusculas.

    SQLite ordena por bytes: "Álgebra" caeria despues de "Física" porque la Á
    tiene un code point mas alto que la F. Con materias en español eso se nota
    a la primera, y el ORDER BY del motor no es portable entre SQLite y
    Postgres, asi que el orden se resuelve aca.
    """
    sin_acentos = unicodedata.normalize("NFKD", name)
    return "".join(c for c in sin_acentos if not unicodedata.combining(c)).lower()


class StudyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Materias ─────────────────────────────────────────────────────────────

    async def list_subjects(self, user_id: str) -> list[Subject]:
        result = await self.db.execute(select(Subject).where(Subject.user_id == user_id))
        return sorted(result.scalars().all(), key=lambda s: _alphabetical_key(s.name))

    async def _get_subject(self, user_id: str, subject_id: str) -> Subject:
        return await get_by_id_or_404(
            self.db, Subject, subject_id, user_id, not_found_detail="Materia no encontrada"
        )

    def _validate_status(self, status: Optional[str]) -> None:
        if status is not None and status not in SUBJECT_STATUSES:
            raise HTTPException(status_code=422, detail="Estado de materia inválido")

    async def create_subject(
        self,
        user_id: str,
        name: str,
        professor: Optional[str] = None,
        color: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Subject:
        self._validate_status(status)
        subject = Subject(
            user_id=user_id,
            name=name,
            professor=professor or None,
            color=color or "#6366F1",
            status=status or SubjectStatus.CURSANDO,
        )
        self.db.add(subject)
        await self.db.commit()
        await self.db.refresh(subject)
        return subject

    async def update_subject(self, user_id: str, subject_id: str, changes: dict) -> Subject:
        subject = await self._get_subject(user_id, subject_id)
        self._validate_status(changes.get("status"))
        apply_changes(subject, changes)
        await self.db.commit()
        await self.db.refresh(subject)
        return subject

    async def delete_subject(self, user_id: str, subject_id: str) -> None:
        subject = await self._get_subject(user_id, subject_id)
        # Los examenes se borran explicitamente: sin esto quedan apuntando a una
        # materia que ya no existe (no hay ON DELETE CASCADE, y SQLite ni
        # siquiera aplica las FKs).
        await self.db.execute(delete(Exam).where(Exam.subject_id == subject.id))
        await self.db.delete(subject)
        await self.db.commit()

    # ── Examenes ─────────────────────────────────────────────────────────────

    async def list_exams(
        self, user_id: str, upcoming: bool = False, tz_offset_minutes: Optional[int] = None
    ) -> list[Exam]:
        query = select(Exam).where(Exam.user_id == user_id)
        if upcoming:
            query = query.where(Exam.exam_date >= local_today(tz_offset_minutes)).order_by(Exam.exam_date)
        else:
            query = query.order_by(Exam.exam_date.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _get_exam(self, user_id: str, exam_id: str) -> Exam:
        return await get_by_id_or_404(
            self.db, Exam, exam_id, user_id, not_found_detail="Examen no encontrado"
        )

    async def create_exam(
        self,
        user_id: str,
        subject_id: str,
        title: str,
        exam_date: date,
        grade: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Exam:
        # Valida de paso que la materia sea de este usuario: sin esto se podrian
        # colgar examenes de la materia de otro.
        await self._get_subject(user_id, subject_id)

        exam = Exam(
            user_id=user_id,
            subject_id=subject_id,
            title=title,
            exam_date=exam_date,
            grade=grade,
            notes=notes or None,
        )
        self.db.add(exam)
        await self.db.commit()
        await self.db.refresh(exam)
        return exam

    async def update_exam(self, user_id: str, exam_id: str, changes: dict) -> Exam:
        exam = await self._get_exam(user_id, exam_id)
        if "subject_id" in changes:
            # subject_id es Optional en el schema de PATCH (para no obligar a
            # mandarlo), pero la columna es NOT NULL: un examen siempre
            # pertenece a una materia. Null explicito se rechaza en vez de
            # dejar que rompa el commit con un IntegrityError.
            if changes["subject_id"] is None:
                raise HTTPException(status_code=422, detail="subject_id no puede ser nulo")
            await self._get_subject(user_id, changes["subject_id"])
        apply_changes(exam, changes)
        await self.db.commit()
        await self.db.refresh(exam)
        return exam

    async def delete_exam(self, user_id: str, exam_id: str) -> None:
        exam = await self._get_exam(user_id, exam_id)
        await self.db.delete(exam)
        await self.db.commit()

    # ── Resumen ──────────────────────────────────────────────────────────────

    async def summary(self, user_id: str, tz_offset_minutes: Optional[int] = None) -> dict:
        subject_result = await self.db.execute(
            select(
                func.count(Subject.id),
                func.sum(case((Subject.status == SubjectStatus.CURSANDO, 1), else_=0)),
                func.sum(case((Subject.status == SubjectStatus.APROBADA, 1), else_=0)),
            ).where(Subject.user_id == user_id)
        )
        subjects_total, subjects_cursando, subjects_aprobadas = subject_result.one()

        today = local_today(tz_offset_minutes)
        exam_result = await self.db.execute(
            select(
                func.avg(Exam.grade),
                func.sum(case((Exam.exam_date >= today, 1), else_=0)),
            ).where(Exam.user_id == user_id)
        )
        average_grade, upcoming_count = exam_result.one()

        next_exam_result = await self.db.execute(
            select(Exam)
            .where(Exam.user_id == user_id, Exam.exam_date >= today)
            .order_by(Exam.exam_date)
            .limit(1)
        )
        next_exam = next_exam_result.scalar_one_or_none()

        return {
            "subjects_total": subjects_total or 0,
            "subjects_cursando": subjects_cursando or 0,
            "subjects_aprobadas": subjects_aprobadas or 0,
            "average_grade": round(average_grade, 2) if average_grade is not None else None,
            "next_exam": next_exam,
            "upcoming_count": upcoming_count or 0,
        }

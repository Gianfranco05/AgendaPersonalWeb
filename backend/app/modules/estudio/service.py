import unicodedata
from datetime import date
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

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
        result = await self.db.execute(
            select(Subject).where(Subject.id == subject_id, Subject.user_id == user_id)
        )
        subject = result.scalar_one_or_none()
        if subject is None:
            raise HTTPException(status_code=404, detail="Materia no encontrada")
        return subject

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
        for field, value in changes.items():
            if value is not None:
                setattr(subject, field, value)
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

    async def list_exams(self, user_id: str, upcoming: bool = False) -> list[Exam]:
        query = select(Exam).where(Exam.user_id == user_id)
        if upcoming:
            query = query.where(Exam.exam_date >= date.today()).order_by(Exam.exam_date)
        else:
            query = query.order_by(Exam.exam_date.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _get_exam(self, user_id: str, exam_id: str) -> Exam:
        result = await self.db.execute(
            select(Exam).where(Exam.id == exam_id, Exam.user_id == user_id)
        )
        exam = result.scalar_one_or_none()
        if exam is None:
            raise HTTPException(status_code=404, detail="Examen no encontrado")
        return exam

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
        if changes.get("subject_id") is not None:
            await self._get_subject(user_id, changes["subject_id"])
        for field, value in changes.items():
            if value is not None:
                setattr(exam, field, value)
        await self.db.commit()
        await self.db.refresh(exam)
        return exam

    async def delete_exam(self, user_id: str, exam_id: str) -> None:
        exam = await self._get_exam(user_id, exam_id)
        await self.db.delete(exam)
        await self.db.commit()

    # ── Resumen ──────────────────────────────────────────────────────────────

    async def summary(self, user_id: str) -> dict:
        subjects = await self.list_subjects(user_id)
        exams = await self.list_exams(user_id)

        graded = [e.grade for e in exams if e.grade is not None]
        upcoming = [e for e in exams if e.exam_date >= date.today()]
        upcoming.sort(key=lambda e: e.exam_date)

        return {
            "subjects_total": len(subjects),
            "subjects_cursando": sum(
                1 for s in subjects if s.status == SubjectStatus.CURSANDO
            ),
            "subjects_aprobadas": sum(
                1 for s in subjects if s.status == SubjectStatus.APROBADA
            ),
            "average_grade": round(sum(graded) / len(graded), 2) if graded else None,
            "next_exam": upcoming[0] if upcoming else None,
            "upcoming_count": len(upcoming),
        }

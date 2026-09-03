from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.focus.models import FocusSession

# Cuantas sesiones recientes mira el resumen. El corte por dia/semana se hace en
# Python y no en SQL a proposito: las columnas son DateTime(timezone=True), y
# SQLite (dev/tests) las devuelve naive mientras Postgres (prod) las devuelve
# aware — comparar contra un bound atado en la query se comporta distinto en
# cada motor. Con este tope el calculo es identico en los dos y sigue cubriendo
# muchisimo mas que una semana de uso real.
_SUMMARY_SCAN_LIMIT = 500


def _as_utc(value: datetime) -> datetime:
    """Normaliza a aware-UTC: SQLite devuelve datetimes naive."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _local_day_start_utc(now_utc: datetime, tz_offset_minutes: int) -> datetime:
    """Medianoche local de hoy, expresada en UTC."""
    offset = timedelta(minutes=tz_offset_minutes)
    local_now = now_utc + offset
    local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_midnight - offset


class FocusService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active(self, user_id: str) -> Optional[FocusSession]:
        result = await self.db.execute(
            select(FocusSession).where(
                FocusSession.user_id == user_id, FocusSession.ended_at.is_(None)
            )
        )
        return result.scalars().first()

    async def start(self, user_id: str, label: Optional[str] = None) -> FocusSession:
        # Idempotente: si ya hay una corriendo se devuelve esa. El doble tap es
        # el modo de falla real en un celular, y abrir dos sesiones en paralelo
        # rompe el invariante de "una activa por usuario".
        active = await self.get_active(user_id)
        if active is not None:
            return active

        session = FocusSession(
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            label=label or None,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def stop(self, user_id: str) -> FocusSession:
        session = await self.get_active(user_id)
        if session is None:
            raise HTTPException(status_code=404, detail="No hay una sesión en curso")

        ended_at = datetime.now(timezone.utc)
        session.ended_at = ended_at
        session.duration_seconds = max(
            0, int((ended_at - _as_utc(session.started_at)).total_seconds())
        )
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def list_recent(self, user_id: str, limit: int = 20) -> list[FocusSession]:
        result = await self.db.execute(
            select(FocusSession)
            .where(FocusSession.user_id == user_id)
            .order_by(FocusSession.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete(self, user_id: str, session_id: str) -> None:
        result = await self.db.execute(
            select(FocusSession).where(
                FocusSession.id == session_id, FocusSession.user_id == user_id
            )
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")
        await self.db.delete(session)
        await self.db.commit()

    async def summary(self, user_id: str, tz_offset_minutes: int = 0) -> dict:
        """Segundos acumulados hoy y esta semana, mas la sesion en curso.

        Solo suma sesiones ya cerradas: los segundos que corren en la sesion
        activa los agrega el cliente, que es el que tiene el reloj andando.
        """
        sessions = await self.list_recent(user_id, limit=_SUMMARY_SCAN_LIMIT)

        now_utc = datetime.now(timezone.utc)
        day_start = _local_day_start_utc(now_utc, tz_offset_minutes)
        local_weekday = (now_utc + timedelta(minutes=tz_offset_minutes)).weekday()
        week_start = day_start - timedelta(days=local_weekday)

        today_seconds = 0
        week_seconds = 0
        for s in sessions:
            if s.duration_seconds is None:
                continue  # sesion en curso
            started = _as_utc(s.started_at)
            if started >= week_start:
                week_seconds += s.duration_seconds
            if started >= day_start:
                today_seconds += s.duration_seconds

        return {
            "today_seconds": today_seconds,
            "week_seconds": week_seconds,
            "active": await self.get_active(user_id),
        }

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select

from app.core.redis_claim import claim_once
from app.database import AsyncSessionLocal
from app.modules.push.service import PushService
from app.modules.recordatorios.models import Reminder

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60

# Dedup en memoria: sin esto, dos ciclos del loop que caigan en el mismo
# minuto (o un reinicio del proceso) podrian mandar la misma push dos veces.
# Es el filtro rapido de un solo proceso; el que vale entre procesos es
# `_claim_in_redis`: gunicorn levanta 2*CPU+1 workers y CADA uno corre su
# propio scheduler (el lifespan se ejecuta por worker), asi que sin un claim
# compartido el usuario recibe la misma push N veces.
_sent_today: dict[str, date] = {}

# Ultimo minuto (UTC, truncado) ya revisado por este proceso. Si un ciclo se
# atrasa y se saltea un minuto (el sleep de 60s mas lo que tarda el ciclo hace
# que el intervalo real sea > 60s), el siguiente ciclo recupera los minutos
# perdidos en vez de dejar sin sonar al recordatorio que caia justo ahi.
_last_checked_minute: Optional[datetime] = None
# Tope de recuperacion: tras una caida larga no se disparan recordatorios viejos.
MAX_CATCHUP_MINUTES = 3


def should_fire(reminder: Reminder, now_utc: datetime) -> bool:
    """True si a este recordatorio le toca sonar ahora mismo (con margen de
    un minuto, que es la resolucion del loop).

    `timezone_offset_minutes=None` (cliente viejo, o recordatorio creado
    offline que todavia no sincronizo) => nunca dispara por server, se queda
    solo con la programacion local del dispositivo.
    """
    if not reminder.enabled or reminder.timezone_offset_minutes is None:
        return False

    local_now = now_utc + timedelta(minutes=reminder.timezone_offset_minutes)
    if (local_now.hour, local_now.minute) != (reminder.hour, reminder.minute):
        return False

    if _sent_today.get(reminder.id) == local_now.date():
        return False

    return True


async def _claim_in_redis(reminder_id: str, local_date: date) -> bool:
    """True si este proceso es el primero en reclamar el disparo (recordatorio,
    dia). Ver `claim_once`: sin Redis, o con Redis caido, manda igual."""
    # 36h: cubre el dia local completo en cualquier huso horario.
    return await claim_once(f"reminder-fired:{reminder_id}:{local_date.isoformat()}", 129600)


def _minutes_to_check(now_utc: datetime) -> list[datetime]:
    """Minutos (UTC, truncados) que este ciclo tiene que revisar: el actual y
    los que se hayan saltado desde el ultimo ciclo."""
    global _last_checked_minute
    current = now_utc.replace(second=0, microsecond=0)
    start = current
    if _last_checked_minute is not None and _last_checked_minute < current:
        start = max(
            _last_checked_minute + timedelta(minutes=1),
            current - timedelta(minutes=MAX_CATCHUP_MINUTES),
        )
    _last_checked_minute = current
    minutes = []
    minute = start
    while minute <= current:
        minutes.append(minute)
        minute += timedelta(minutes=1)
    return minutes


async def _tick() -> None:
    now_utc = datetime.now(timezone.utc)
    minutes = _minutes_to_check(now_utc)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Reminder).where(
                Reminder.enabled == True,  # noqa: E712
                Reminder.timezone_offset_minutes.is_not(None),
            )
        )
        reminders = result.scalars().all()

        push = PushService(db)
        for reminder in reminders:
            fire_at = next((m for m in minutes if should_fire(reminder, m)), None)
            if fire_at is None:
                continue
            local_date = (fire_at + timedelta(minutes=reminder.timezone_offset_minutes)).date()
            _sent_today[reminder.id] = local_date
            if not await _claim_in_redis(reminder.id, local_date):
                continue
            try:
                await push.send_to_user(
                    reminder.user_id,
                    f"{reminder.icon} Can_cen",
                    reminder.message,
                    data={"type": "reminder", "reminder_id": reminder.id},
                )
            except Exception:
                logger.exception("Fallo mandando la push del recordatorio %s", reminder.id)

    # El dict de dedup solo necesita la fecha de hoy: una entrada de ayer no
    # sirve para nada y se acumularia para siempre en un proceso de larga vida.
    # Con husos de +14h a -12h el "hoy" local puede ser ayer o manana de UTC:
    # se conserva todo lo que no sea anterior a ayer UTC.
    cutoff = now_utc.date() - timedelta(days=1)
    stale = [rid for rid, sent_date in _sent_today.items() if sent_date < cutoff]
    for rid in stale:
        del _sent_today[rid]


async def run_reminder_scheduler() -> None:
    """Loop de fondo, arrancado desde el lifespan de la app. Un tick fallido
    (DB caida un instante, Expo caido) no debe tumbar el loop entero —
    cada `_tick()` ya atrapa sus propios errores por recordatorio, y esto es
    un cinturon extra por si algo se escapa igual.
    """
    while True:
        try:
            await _tick()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Fallo un ciclo del scheduler de recordatorios")
        # Alineado al inicio del minuto siguiente: con un sleep fijo de 60s mas
        # lo que tarda el ciclo, el loop se va corriendo y cada tanto un minuto
        # entero queda sin revisar.
        now = datetime.now(timezone.utc)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS - now.second - now.microsecond / 1e6 + 1)

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.modules.push.service import PushService
from app.modules.recordatorios.models import Reminder

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60

# Dedup en memoria: sin esto, dos ciclos del loop que caigan en el mismo
# minuto (o un reinicio del proceso) podrian mandar la misma push dos veces.
# Vive en el proceso (no en Redis/DB) — igual que el rate limiter en memoria
# de app/core/http_security.py, alcanza con una sola instancia de backend;
# con mas de una replica cada proceso dedupea por separado y una push podria
# duplicarse entre replicas.
_sent_today: dict[str, date] = {}


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


async def _tick() -> None:
    now_utc = datetime.now(timezone.utc)
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
            if not should_fire(reminder, now_utc):
                continue
            local_date = (now_utc + timedelta(minutes=reminder.timezone_offset_minutes)).date()
            _sent_today[reminder.id] = local_date
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
    today = now_utc.date()
    stale = [rid for rid, sent_date in _sent_today.items() if sent_date != today]
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
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)

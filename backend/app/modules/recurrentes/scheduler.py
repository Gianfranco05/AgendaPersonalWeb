"""Generacion automatica de movimientos recurrentes.

Un ciclo por minuto en cada worker de gunicorn. Cada plantilla se procesa solo
dentro de la ventana horaria LOCAL del usuario (09:00-21:59): las push nunca
salen de madrugada y, si el server estuvo caido a las 9, se recupera en el
primer ciclo dentro de la ventana (con la fecha original de cada movimiento).

No hace falta Redis ni memoria en proceso: la exactitud (una sola
transaccion por plantilla y fecha) la garantiza la base con un compare-and-set
del cursor + restriccion unica (ver `service.materialize`). Los workers que
pierden la carrera simplemente no hacen nada y, como solo se manda la push de
lo que el propio worker commiteo, tampoco la duplican.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.database import AsyncSessionLocal
from app.modules.push.service import PushService
from app.modules.recurrentes import rules
from app.modules.recurrentes.notifications import notify_generated
from app.modules.recurrentes.repository import RecurringRepository
from app.modules.recurrentes.service import Generated, RecurringService

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60
WINDOW_START_HOUR = 9
WINDOW_END_HOUR = 22  # exclusivo: el ultimo ciclo valido es 21:59


async def _tick(now_utc: Optional[datetime] = None) -> list[Generated]:
    now_utc = now_utc or datetime.now(timezone.utc)
    generated: list[Generated] = []
    async with AsyncSessionLocal() as db:
        repo = RecurringRepository(db)
        service = RecurringService(db)
        # Se copian los datos que se necesitan: un rollback expira los objetos
        # y en async leerlos despues revienta.
        due = [
            (r.id, r.user_id, r.timezone_offset_minutes, r.next_occurrence_date)
            for r in await repo.list_due(now_utc.date())
        ]
        for rec_id, user_id, offset, cursor in due:
            local = rules.local_now(now_utc, offset)
            if not (WINDOW_START_HOUR <= local.hour < WINDOW_END_HOUR):
                continue
            today = local.date()
            if cursor is None or cursor > today:
                continue
            try:
                rec = await repo.get(rec_id, user_id)
                if rec is None:
                    continue
                result = await service.materialize(rec, today)
                generated.extend(result.items)
            except Exception:
                # Una plantilla rota no frena a las demas ni al loop; el proximo
                # ciclo la reintenta (todo se revirtio).
                await db.rollback()
                logger.exception("Fallo la generacion de la recurrente %s", rec_id)

        if generated:
            await notify_generated(PushService(db), generated)
    return generated


async def run_recurring_scheduler() -> None:
    """Loop de fondo arrancado desde el lifespan. Un ciclo fallido (DB caida un
    instante) se loguea y el loop sigue."""
    while True:
        try:
            await _tick()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Fallo un ciclo del scheduler de recurrentes")
        now = datetime.now(timezone.utc)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS - now.second - now.microsecond / 1e6 + 1)

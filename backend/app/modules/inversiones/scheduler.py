"""Avisos de vencimiento de inversiones (push, via Expo).

Un aviso el dia anterior ("Vence manana") y otro el dia del vencimiento
("Vence hoy"), desde las 09:00 locales. A diferencia de los recordatorios, que
disparan en un minuto exacto, aca hay una VENTANA (09:00-21:59 locales): si el
server estuvo caido a las 9, el aviso sale en el primer ciclo dentro de la
ventana. Para que un ciclo por minuto no mande el mismo aviso 780 veces, ni
varios workers de gunicorn (cada uno corre su scheduler) lo dupliquen, hay tres
capas de dedup, de la mas barata a la que decide:

1. un set en memoria por proceso;
2. un claim `SET NX` en Redis compartido entre workers (se saltea sin Redis);
3. una marca persistente y atomica en la fila (`eve_notice_for` /
   `day_notice_for` = fecha de vencimiento): solo manda quien logra cambiarla.
   Cubre reinicios del proceso y despliegues sin Redis.

Semantica at-most-once: la marca se escribe antes de mandar, asi que si Expo
falla el aviso se pierde (igual que los recordatorios).
"""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from app.core.redis_claim import claim_once
from app.database import AsyncSessionLocal
from app.modules.inversiones.models import Investment
from app.modules.inversiones.repository import InvestmentRepository
from app.modules.inversiones.valuation import format_money_es_ar, valuate
from app.modules.push.service import PushService

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60
#: Argentina: el mercado de la app. Se usa cuando el cliente no mando el offset.
DEFAULT_TZ_OFFSET_MINUTES = -180
WINDOW_START_HOUR = 9
WINDOW_END_HOUR = 22  # exclusivo: el ultimo ciclo valido es 21:59
#: 36 h cubre el dia local completo en cualquier huso horario.
CLAIM_TTL_SECONDS = 129600

#: (investment_id, kind, maturity_date) ya procesados por este proceso.
_handled: set[tuple[str, str, date]] = set()


def due_kind(inv: Investment, now_utc: datetime) -> Optional[str]:
    """`eve` (vence manana), `day` (vence hoy) o None si hoy no toca avisar:
    fuera de la ventana horaria local o vencimiento a otra distancia."""
    if inv.maturity_date is None:
        return None
    offset = (
        inv.timezone_offset_minutes
        if inv.timezone_offset_minutes is not None
        else DEFAULT_TZ_OFFSET_MINUTES
    )
    local_now = now_utc + timedelta(minutes=offset)
    if not (WINDOW_START_HOUR <= local_now.hour < WINDOW_END_HOUR):
        return None
    days_left = (inv.maturity_date - local_now.date()).days
    if days_left == 1:
        return "eve"
    if days_left == 0:
        return "day"
    return None


def build_message(inv: Investment, kind: str, local_today: date) -> tuple[str, str]:
    when = "mañana" if kind == "eve" else "hoy"
    title = f"Vence {when}: {inv.name}"
    fixed_term = valuate(inv, local_today).fixed_term
    if fixed_term is not None:
        where = f" en {inv.institution}" if inv.institution else ""
        body = (
            f"Tu plazo fijo{where} cobra "
            f"{format_money_es_ar(fixed_term.amount_at_maturity, inv.currency)}."
        )
    else:
        body = f"{inv.name} vence {when}."
    return title, body


async def _process(
    repo: InvestmentRepository, push: PushService, inv: Investment, now_utc: datetime
) -> None:
    kind = due_kind(inv, now_utc)
    if kind is None:
        return
    maturity = inv.maturity_date
    handled_key = (inv.id, kind, maturity)
    if handled_key in _handled:
        return
    _handled.add(handled_key)

    try:
        if not await claim_once(
            f"investment-maturity:{inv.id}:{kind}:{maturity.isoformat()}", CLAIM_TTL_SECONDS
        ):
            return
        if not await repo.claim_notice(inv.id, kind, maturity):
            return
    except Exception:
        # La marca persistente no se escribio (DB caida un instante): se
        # reintenta en el proximo ciclo en vez de darlo por procesado.
        _handled.discard(handled_key)
        raise

    offset = (
        inv.timezone_offset_minutes
        if inv.timezone_offset_minutes is not None
        else DEFAULT_TZ_OFFSET_MINUTES
    )
    title, body = build_message(inv, kind, (now_utc + timedelta(minutes=offset)).date())
    await push.send_to_user(
        inv.user_id,
        title,
        body,
        data={"type": "investment_maturity", "investment_id": inv.id},
    )


async def _tick(now_utc: Optional[datetime] = None) -> None:
    now_utc = now_utc or datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        repo = InvestmentRepository(db)
        investments = await repo.list_due_for_alerts(now_utc.date())
        push = PushService(db)
        for inv in investments:
            try:
                await _process(repo, push, inv, now_utc)
            except Exception:
                # Un activo roto (o Expo caido) no frena a los demas ni al loop.
                logger.exception("Fallo el aviso de vencimiento de la inversion %s", inv.id)

    # El set solo necesita los vencimientos cercanos: se poda lo viejo para que
    # no crezca para siempre en un proceso de larga vida.
    cutoff = now_utc.date() - timedelta(days=2)
    for stale in [k for k in _handled if k[2] < cutoff]:
        _handled.discard(stale)


async def run_investment_alert_scheduler() -> None:
    """Loop de fondo arrancado desde el lifespan, un ciclo por minuto. Un ciclo
    fallido (DB caida un instante) se loguea y el loop sigue."""
    while True:
        try:
            await _tick()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Fallo un ciclo del scheduler de vencimientos")
        now = datetime.now(timezone.utc)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS - now.second - now.microsecond / 1e6 + 1)

"""Push de los movimientos recurrentes (via Expo, canal `recordatorios`).

Se mandan DESPUES del commit y solo por lo que ESTE worker commiteo, una push
por usuario y ciclo: si hay mas de un movimiento notificable se manda un
resumen. Los errores de Expo se loguean y nunca tocan lo ya generado (la push
es at-most-once; la transaccion es exactly-once).
"""

import logging
from collections import defaultdict
from typing import Optional

from app.modules.inversiones.valuation import format_money_es_ar
from app.modules.push.service import PushService
from app.modules.recurrentes.service import Generated

logger = logging.getLogger(__name__)


def _plural(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def build_message(items: list[Generated]) -> Optional[tuple[str, str, dict]]:
    """(titulo, cuerpo, data) para los movimientos notificables de un usuario."""
    if not items:
        return None
    if len(items) == 1:
        item = items[0]
        if item.kind == "generated":
            kind = "Ingreso" if item.type == "income" else "Gasto"
            where = f" en {item.bank_label}" if item.bank_label else ""
            return (
                f"Se registró: {item.name}",
                f"{kind} de {format_money_es_ar(item.amount, item.currency)}{where}.",
                {
                    "type": "recurring_generated",
                    "recurrence_id": item.recurrence_id,
                    "transaction_id": item.transaction_id,
                },
            )
        if item.amount is not None:
            body = (
                f"Estimado {format_money_es_ar(item.amount, item.currency)}. "
                "Tocá para confirmarlo o editarlo."
            )
        else:
            body = "Tocá para cargar el monto."
        return (
            f"Confirmá el monto: {item.name}",
            body,
            {
                "type": "recurring_confirm",
                "occurrence_id": item.occurrence_id,
                "recurrence_id": item.recurrence_id,
            },
        )

    registered = sum(1 for i in items if i.kind == "generated")
    to_confirm = sum(1 for i in items if i.kind == "pending")
    parts = []
    if registered:
        parts.append(
            f"Se {'registró' if registered == 1 else 'registraron'} "
            f"{_plural(registered, 'movimiento', 'movimientos')}"
        )
    if to_confirm:
        if registered:
            parts.append(f"tenés {to_confirm} para confirmar")
        else:
            parts.append(f"Tenés {_plural(to_confirm, 'movimiento', 'movimientos')} para confirmar")
    body = " y ".join(parts) + "."
    return "Movimientos recurrentes", body, {"type": "recurring_summary"}


async def notify_generated(push: PushService, items: list[Generated]) -> None:
    """Agrupa por usuario (solo plantillas con `notify`) y manda una push a cada uno."""
    by_user: dict[str, list[Generated]] = defaultdict(list)
    for item in items:
        if item.notify:
            by_user[item.user_id].append(item)
    for user_id, user_items in by_user.items():
        message = build_message(user_items)
        if message is None:
            continue
        title, body, data = message
        try:
            await push.send_to_user(user_id, title, body, data=data)
        except Exception:
            logger.exception("Fallo la push de recurrentes del usuario %s", user_id)

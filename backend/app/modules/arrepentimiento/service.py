import html
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import send_withdrawal_confirmation_email
from app.core.notifier import send_telegram_alert
from app.modules.arrepentimiento.models import WithdrawalRequest
from app.modules.auth.models import User
from app.modules.modulos.models import ModulePurchase

logger = logging.getLogger(__name__)

# Sin 0/O ni 1/I/L: el codigo se dicta o se copia a mano en un reclamo.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6
CODE_PREFIX = "ARR-"
CODE_ATTEMPTS = 5

#: Plazo de la politica de reembolsos (la ley da 10 dias; la politica, 14).
REFUND_WINDOW_DAYS = 14


def generate_code() -> str:
    return CODE_PREFIX + "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def _as_utc(value: datetime) -> datetime:
    # SQLite devuelve datetimes naive aunque la columna sea timezone-aware.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class WithdrawalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _is_outside_window(self, user_id: Optional[str], email: str) -> bool:
        """True si las compras conocidas de la persona son todas mas viejas que
        el plazo. Sin compras identificables devuelve False: no hay nada que
        comparar, y el operador igual verifica la compra a mano."""
        if user_id is None:
            result = await self.db.execute(
                select(User.id).where(func.lower(User.email) == email.lower())
            )
            user_id = result.scalar_one_or_none()
        if user_id is None:
            return False

        result = await self.db.execute(
            select(ModulePurchase.created_at).where(ModulePurchase.user_id == str(user_id))
        )
        fechas = [_as_utc(f) for f in result.scalars().all() if f is not None]
        if not fechas:
            return False
        limite = datetime.now(timezone.utc) - timedelta(days=REFUND_WINDOW_DAYS)
        return max(fechas) < limite

    async def create(
        self,
        *,
        full_name: str,
        email: str,
        purchase_detail: str,
        message: Optional[str],
        user_id: Optional[str],
    ) -> WithdrawalRequest:
        needs_review = await self._is_outside_window(user_id, email)

        request: Optional[WithdrawalRequest] = None
        for _ in range(CODE_ATTEMPTS):
            candidate = WithdrawalRequest(
                code=generate_code(),
                full_name=full_name,
                email=email,
                purchase_detail=purchase_detail,
                message=message,
                user_id=user_id,
                needs_review=needs_review,
            )
            self.db.add(candidate)
            try:
                await self.db.commit()
            except IntegrityError:
                # Colision de codigo (muy improbable): se reintenta con otro.
                await self.db.rollback()
                continue
            request = candidate
            break

        if request is None:
            raise RuntimeError("No se pudo generar un codigo de tramite unico")

        logger.info(
            "Solicitud de arrepentimiento %s | user_id=%s | needs_review=%s",
            request.code,
            user_id,
            needs_review,
        )
        await self._notify(request)
        return request

    async def _notify(self, request: WithdrawalRequest) -> None:
        """Mail al solicitante y aviso al operador. Ninguno puede romper el
        pedido: la solicitud ya esta guardada y es lo que cuenta legalmente."""
        try:
            await send_withdrawal_confirmation_email(
                request.email, request.code, request.full_name
            )
        except Exception:
            logger.exception(
                "Fallo el mail de confirmacion de la solicitud %s", request.code
            )

        try:
            aviso = (
                "<b>Botón de arrepentimiento</b>\n"
                f"Código: <code>{request.code}</code>\n"
                f"Nombre: {html.escape(request.full_name)}\n"
                f"Email: {html.escape(request.email)}\n"
                f"Compra: {html.escape(request.purchase_detail[:300])}"
            )
            if request.needs_review:
                aviso += (
                    "\n<b>Revisar a mano:</b> la última compra es anterior a "
                    f"{REFUND_WINDOW_DAYS} días."
                )
            # event_type propio por solicitud: el cooldown del notifier es por
            # tipo de evento y taparia pedidos distintos llegados seguidos.
            await send_telegram_alert(aviso, event_type=f"withdrawal:{request.code}")
        except Exception:
            logger.exception("Fallo el aviso al operador de la solicitud %s", request.code)

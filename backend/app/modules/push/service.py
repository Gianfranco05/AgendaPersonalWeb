import logging
from typing import Any, Optional

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.push.models import PushToken

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


class PushService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, user_id: str, token: str, device_info: Optional[str] = None) -> PushToken:
        result = await self.db.execute(select(PushToken).where(PushToken.token == token))
        existing = result.scalar_one_or_none()
        if existing:
            # Reasigna el token al usuario logueado ahora: si el dispositivo
            # cambio de cuenta (logout + login de otra persona), la cuenta
            # vieja deja de recibir push de este telefono sin que nadie tenga
            # que desregistrar nada a mano.
            existing.user_id = user_id
            existing.device_info = device_info
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        push_token = PushToken(user_id=user_id, token=token, device_info=device_info)
        self.db.add(push_token)
        await self.db.commit()
        await self.db.refresh(push_token)
        return push_token

    async def unregister(self, token: str) -> None:
        await self.db.execute(delete(PushToken).where(PushToken.token == token))
        await self.db.commit()

    async def tokens_for_user(self, user_id: str) -> list[str]:
        result = await self.db.execute(select(PushToken.token).where(PushToken.user_id == user_id))
        return list(result.scalars().all())

    async def send_to_user(
        self, user_id: str, title: str, body: str, data: Optional[dict[str, Any]] = None
    ) -> None:
        """Manda una push a todos los dispositivos del usuario, vía la API de
        Expo. Nunca deja escapar una excepción: quien llama (el scheduler de
        recordatorios) no puede caerse porque Expo esté caído o un token sea
        inválido.
        """
        tokens = await self.tokens_for_user(user_id)
        if not tokens:
            return

        messages = [
            {"to": token, "title": title, "body": body, "data": data or {}, "sound": "default"}
            for token in tokens
        ]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(EXPO_PUSH_URL, json=messages)
                response.raise_for_status()
                results = response.json().get("data", [])
        except Exception:
            logger.exception("Fallo mandando push a Expo para el usuario %s", user_id)
            return

        # Un token puede quedar invalido (desinstalo la app, reseteo el
        # dispositivo). Expo lo informa por mensaje en vez de por HTTP status
        # — sin limpiarlo, cada push futura vuelve a fallar para siempre.
        for token, result in zip(tokens, results):
            if isinstance(result, dict) and result.get("details", {}).get("error") == "DeviceNotRegistered":
                await self.unregister(token)

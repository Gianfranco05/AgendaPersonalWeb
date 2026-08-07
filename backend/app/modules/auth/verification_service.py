from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_refresh_token, hash_refresh_token
from app.modules.auth.models import User, VerificationPurpose, VerificationToken

_TTL_HOURS = {
    VerificationPurpose.EMAIL_VERIFY: lambda: settings.EMAIL_VERIFY_TOKEN_EXPIRE_HOURS,
    VerificationPurpose.PASSWORD_RESET: lambda: settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS,
}


class VerificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def issue(self, user_id: str, purpose: str) -> str:
        """Invalida los tokens previos del mismo proposito y emite uno nuevo.

        Pedir un link nuevo tiene que matar el anterior: si no, cada pedido deja
        otro token vivo y ampliar la ventana de ataque sale gratis.
        """
        await self.db.execute(
            update(VerificationToken)
            .where(
                VerificationToken.user_id == str(user_id),
                VerificationToken.purpose == purpose,
                VerificationToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(timezone.utc))
        )

        raw = create_refresh_token()
        ttl_hours = _TTL_HOURS[purpose]()
        self.db.add(
            VerificationToken(
                user_id=str(user_id),
                token_hash=hash_refresh_token(raw),
                purpose=purpose,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
            )
        )
        await self.db.commit()
        return raw

    async def consume(self, raw_token: str, purpose: str) -> Optional[User]:
        """Valida y marca el token como usado. None si no sirve."""
        result = await self.db.execute(
            select(VerificationToken).where(
                VerificationToken.token_hash == hash_refresh_token(raw_token),
                VerificationToken.purpose == purpose,
            )
        )
        token = result.scalar_one_or_none()
        if token is None or not token.is_usable:
            return None

        user = await self.db.get(User, token.user_id)
        if user is None:
            return None

        token.used_at = datetime.now(timezone.utc)
        await self.db.commit()
        return user

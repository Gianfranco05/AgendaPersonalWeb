from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_refresh_token, hash_refresh_token
from app.modules.auth.models import RefreshToken, User


class RefreshTokenReuseError(Exception):
    """Se presento un token ya revocado — se asume robo y se cierran todas las sesiones."""


class RefreshService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def issue(self, user_id: str, device_info: Optional[str] = None) -> str:
        raw = create_refresh_token()
        token = RefreshToken(
            user_id=str(user_id),
            token_hash=hash_refresh_token(raw),
            device_info=(device_info or "")[:255] or None,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.db.add(token)
        await self.db.commit()
        return raw

    async def _get_by_raw(self, raw_token: str) -> Optional[RefreshToken]:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh_token(raw_token)
            )
        )
        return result.scalar_one_or_none()

    async def rotate(
        self, raw_token: str, device_info: Optional[str] = None
    ) -> tuple[User, str]:
        """Valida el token, lo revoca y emite uno nuevo. Devuelve (user, nuevo_raw).

        La rotacion en cada uso es lo que hace detectable el robo: si alguien
        replica un token viejo, ya esta revocado y caemos en reuse -> se cierran
        todas las sesiones del usuario.
        """
        token = await self._get_by_raw(raw_token)
        if token is None:
            raise ValueError("Refresh token invalido")

        if token.revoked_at is not None:
            await self.revoke_all(token.user_id)
            raise RefreshTokenReuseError("Refresh token ya utilizado")

        if not token.is_active:
            raise ValueError("Refresh token expirado")

        user = await self.db.get(User, token.user_id)
        if user is None or not user.is_active:
            raise ValueError("Usuario invalido")

        now = datetime.now(timezone.utc)
        token.revoked_at = now
        token.last_used_at = now

        new_raw = create_refresh_token()
        self.db.add(
            RefreshToken(
                user_id=token.user_id,
                token_hash=hash_refresh_token(new_raw),
                device_info=(device_info or token.device_info or "")[:255] or None,
                expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            )
        )
        await self.db.commit()
        return user, new_raw

    async def revoke(self, raw_token: str) -> None:
        token = await self._get_by_raw(raw_token)
        if token is not None and token.revoked_at is None:
            token.revoked_at = datetime.now(timezone.utc)
            await self.db.commit()

    async def revoke_all(self, user_id: str) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == str(user_id),
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self.db.commit()

    async def list_active(self, user_id: str) -> Sequence[RefreshToken]:
        result = await self.db.execute(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == str(user_id),
                RefreshToken.revoked_at.is_(None),
            )
            .order_by(RefreshToken.created_at.desc())
        )
        return [t for t in result.scalars().all() if t.is_active]

    async def revoke_session(self, session_id: str, user_id: str) -> bool:
        """Revoca una sesion propia. False si no existe o no es del usuario."""
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.id == session_id,
                RefreshToken.user_id == str(user_id),
                RefreshToken.revoked_at.is_(None),
            )
        )
        token = result.scalar_one_or_none()
        if token is None:
            return False
        token.revoked_at = datetime.now(timezone.utc)
        await self.db.commit()
        return True

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import UserCreate, UserLogin
from app.core.security import hash_password, verify_password


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(self, data: UserCreate) -> tuple[User | None, str | None]:
        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            return None, "Este email ya esta registrado"

        user = User(
            email=data.email,
            full_name=data.full_name,
            password_hash=hash_password(data.password),
        )

        user = await self.user_repo.create(user)
        return user, None

    async def login(self, data: UserLogin) -> tuple[User | None, str | None]:
        user = await self.user_repo.get_by_email(data.email)

        if not user:
            return None, "Email o contrasena incorrectos"

        if not verify_password(data.password, user.password_hash):
            return None, "Email o contrasena incorrectos"

        if not user.is_active:
            return None, "Usuario inactivo"

        return user, None

    async def get_user_by_id(self, user_id) -> Optional[User]:
        return await self.user_repo.get_by_id(user_id)

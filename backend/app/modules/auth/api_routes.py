from fastapi import APIRouter, Depends, Response, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.core.security import verify_password, create_access_token, hash_password
from app.core.dependencies import get_current_user
from app.core.http_security import rate_limit_auth
from app.modules.auth.models import User

router = APIRouter(prefix="/auth/api", tags=["auth-json"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres")
        return v


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str


class UpdateMeRequest(BaseModel):
    full_name: str

    @field_validator("full_name")
    @classmethod
    def full_name_not_empty(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        return v


def _set_cookie(response: Response, user_id: str) -> None:
    token = create_access_token({"sub": str(user_id)})
    response.set_cookie(
        key=settings.JWT_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=not settings.DEBUG,
    )


@router.post("/login", response_model=UserOut, dependencies=[Depends(rate_limit_auth)])
async def api_login(
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    # Upgrade legacy SHA256 → bcrypt transparently
    if not user.password_hash.startswith("$2"):
        user.password_hash = hash_password(data.password)
        db.add(user)
        await db.commit()

    _set_cookie(response, user.id)
    return UserOut(id=str(user.id), email=user.email, full_name=user.full_name)


@router.post("/register", status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit_auth)])
async def api_register(
    data: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == data.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este email ya está registrado",
        )

    user = User(
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    _set_cookie(response, user.id)
    return UserOut(id=str(user.id), email=user.email, full_name=user.full_name)


@router.get("/me", response_model=UserOut)
async def api_me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
    )


@router.patch("/me", response_model=UserOut)
async def api_update_me(
    data: UpdateMeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.full_name = data.full_name
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return UserOut(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
    )


@router.post("/logout")
async def api_logout(response: Response):
    response.delete_cookie(settings.JWT_COOKIE_NAME)
    return {"ok": True}

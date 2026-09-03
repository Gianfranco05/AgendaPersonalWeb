import logging
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.core.security import verify_password, create_access_token, hash_password
from app.core.dependencies import get_current_user
from app.core.http_security import rate_limit_auth
from app.core.redirect_safety import validate_app_redirect
from app.core.email import send_password_reset_email, send_verification_email
from app.modules.auth.models import User, VerificationPurpose
from app.modules.auth.refresh_service import RefreshService, RefreshTokenReuseError
from app.modules.auth.verification_service import VerificationService

logger = logging.getLogger(__name__)

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
    is_verified: bool = True


class AuthResponse(BaseModel):
    id: str
    email: str
    full_name: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    # Opcional: la web manda el refresh por cookie, mobile por body.
    refresh_token: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class SessionOut(BaseModel):
    id: str
    device_info: Optional[str] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: datetime


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres")
        return v


class UpdateMeRequest(BaseModel):
    full_name: str

    @field_validator("full_name")
    @classmethod
    def full_name_not_empty(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        return v


def _set_access_cookie(response: Response, access_token: str) -> None:
    response.set_cookie(
        key=settings.JWT_COOKIE_NAME,
        value=access_token,
        httponly=True,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=not settings.DEBUG,
    )


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        samesite="lax",
        secure=not settings.DEBUG,
    )


async def _issue_session(
    db: AsyncSession, response: Response, request: Request, user: User
) -> tuple[str, str]:
    """Emite access + refresh para un login/registro y los deja en cookies."""
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = await RefreshService(db).issue(
        str(user.id), device_info=request.headers.get("User-Agent")
    )
    _set_access_cookie(response, access_token)
    _set_refresh_cookie(response, refresh_token)
    return access_token, refresh_token


@router.post("/login", response_model=AuthResponse, dependencies=[Depends(rate_limit_auth)])
async def api_login(
    data: LoginRequest,
    request: Request,
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

    access_token, refresh_token = await _issue_session(db, response, request, user)
    return AuthResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=AuthResponse, dependencies=[Depends(rate_limit_auth)])
async def api_register(
    data: RegisterRequest,
    request: Request,
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

    verify_token = await VerificationService(db).issue(
        str(user.id), VerificationPurpose.EMAIL_VERIFY
    )
    await send_verification_email(user.email, verify_token)

    access_token, refresh_token = await _issue_session(db, response, request, user)
    return AuthResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get("/me", response_model=UserOut)
async def api_me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        is_verified=current_user.is_verified,
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
        is_verified=current_user.is_verified,
    )


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(rate_limit_auth)])
async def api_refresh(
    data: RefreshRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    raw = data.refresh_token or request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el refresh token",
        )

    service = RefreshService(db)
    try:
        user, new_refresh = await service.rotate(
            raw, device_info=request.headers.get("User-Agent")
        )
    except RefreshTokenReuseError:
        # Token ya usado: se asume robo, rotate() ya cerro todas las sesiones.
        response.delete_cookie(settings.JWT_COOKIE_NAME)
        response.delete_cookie(settings.REFRESH_COOKIE_NAME)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida. Volvé a iniciar sesión.",
        )
    except ValueError:
        response.delete_cookie(settings.JWT_COOKIE_NAME)
        response.delete_cookie(settings.REFRESH_COOKIE_NAME)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado",
        )

    access_token = create_access_token({"sub": str(user.id)})
    _set_access_cookie(response, access_token)
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.get("/sessions", response_model=list[SessionOut])
async def api_list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tokens = await RefreshService(db).list_active(str(current_user.id))
    return [
        SessionOut(
            id=t.id,
            device_info=t.device_info,
            created_at=t.created_at,
            last_used_at=t.last_used_at,
            expires_at=t.expires_at,
        )
        for t in tokens
    ]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    revoked = await RefreshService(db).revoke_session(session_id, str(current_user.id))
    if not revoked:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")


@router.post("/verify-email/request", dependencies=[Depends(rate_limit_auth)])
async def api_request_verification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.is_verified:
        return {"ok": True, "already_verified": True}

    token = await VerificationService(db).issue(
        str(current_user.id), VerificationPurpose.EMAIL_VERIFY
    )
    await send_verification_email(current_user.email, token)
    return {"ok": True, "already_verified": False}


@router.post("/verify-email", response_model=UserOut, dependencies=[Depends(rate_limit_auth)])
async def api_verify_email(
    data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await VerificationService(db).consume(
        data.token, VerificationPurpose.EMAIL_VERIFY
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link de verificación inválido o vencido",
        )

    user.is_verified = True
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_verified=user.is_verified,
    )


@router.post("/forgot-password", dependencies=[Depends(rate_limit_auth)])
async def api_forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user is not None and user.is_active:
        token = await VerificationService(db).issue(
            str(user.id), VerificationPurpose.PASSWORD_RESET
        )
        await send_password_reset_email(user.email, token)

    # Respuesta identica exista o no la cuenta: si no, este endpoint sirve para
    # averiguar que emails estan registrados.
    return {"ok": True}


@router.post("/reset-password", dependencies=[Depends(rate_limit_auth)])
async def api_reset_password(
    data: ResetPasswordRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user = await VerificationService(db).consume(
        data.token, VerificationPurpose.PASSWORD_RESET
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link de recuperación inválido o vencido",
        )

    user.password_hash = hash_password(data.password)
    db.add(user)
    await db.commit()

    # Cambiar la contraseña tiene que echar al que la haya robado: si no, sus
    # sesiones siguen vivas hasta 30 dias con la contraseña vieja ya cambiada.
    await RefreshService(db).revoke_all(str(user.id))
    response.delete_cookie(settings.JWT_COOKIE_NAME)
    response.delete_cookie(settings.REFRESH_COOKIE_NAME)
    return {"ok": True}


@router.post("/logout")
async def api_logout(
    request: Request,
    response: Response,
    data: Optional[RefreshRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    # Mobile no tiene cookies: manda el refresh en el body para poder revocarlo.
    # Sin esto su sesion sigue viva en el server hasta vencer, aunque el celular
    # ya haya borrado el token.
    raw = (data.refresh_token if data else None) or request.cookies.get(
        settings.REFRESH_COOKIE_NAME
    )
    if raw:
        await RefreshService(db).revoke(raw)
    response.delete_cookie(settings.JWT_COOKIE_NAME)
    response.delete_cookie(settings.REFRESH_COOKIE_NAME)
    return {"ok": True}


# ── Iniciar sesion con Google ──────────────────────────────────────────────
#
# El intercambio con Google lo hace siempre el backend, nunca el cliente: el
# celular no puede guardar un client secret con seguridad. El flujo es:
#
#   1. GET /google/login?app_redirect=<url a la que el navegador debe volver
#      dentro de la app> -> redirige a la pantalla de consentimiento de
#      Google, con esta URL viajando (firmada) en el parametro `state`.
#   2. Google vuelve a GET /google/callback?code&state -> el backend valida
#      el state, canjea el code, verifica la identidad, crea o encuentra al
#      usuario, emite la sesion propia, y redirige de vuelta a `app_redirect`
#      con el access/refresh token en la query string.
#
def _sign_oauth_state(app_redirect: str) -> str:
    import base64
    import hashlib
    import hmac
    import json
    import time

    payload = json.dumps({"r": app_redirect, "exp": time.time() + 300}).encode()
    body = base64.urlsafe_b64encode(payload).decode()
    sig = hmac.new(settings.SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def _verify_oauth_state(state: str) -> Optional[str]:
    import base64
    import hashlib
    import hmac
    import json
    import time

    try:
        body, sig = state.split(".", 1)
        expected = hmac.new(settings.SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body.encode()))
        if payload.get("exp", 0) < time.time():
            return None
        return payload.get("r")
    except Exception:
        return None


def _build_google_login_flow():
    from google_auth_oauthlib.flow import Flow

    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_LOGIN_REDIRECT_URI],
            }
        },
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        redirect_uri=settings.GOOGLE_LOGIN_REDIRECT_URI,
    )


@router.get("/google/login")
async def api_google_login_start(app_redirect: str):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Login con Google no esta configurado")

    validate_app_redirect(app_redirect)

    flow = _build_google_login_flow()
    auth_url, _ = flow.authorization_url(
        access_type="online",
        include_granted_scopes="true",
        prompt="select_account",
        state=_sign_oauth_state(app_redirect),
    )
    return RedirectResponse(url=auth_url, status_code=303)


@router.get("/google/callback")
async def api_google_login_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    app_redirect = _verify_oauth_state(state) if state else None
    if not app_redirect:
        raise HTTPException(status_code=400, detail="Sesión de login inválida o vencida")

    if error or not code:
        return RedirectResponse(url=f"{app_redirect}?error=google_denied", status_code=303)

    try:
        import asyncio

        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token

        flow = _build_google_login_flow()
        await asyncio.to_thread(flow.fetch_token, code=code)
        credentials = flow.credentials

        idinfo = await asyncio.to_thread(
            google_id_token.verify_oauth2_token,
            credentials.id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
        email = idinfo["email"]
        full_name = idinfo.get("name") or email.split("@")[0]
    except Exception:
        logger.exception("Fallo el intercambio de codigo o la verificacion de identidad con Google")
        return RedirectResponse(url=f"{app_redirect}?error=google_failed", status_code=303)

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        # Cuenta nueva, creada solo por Google: el hash es aleatorio e
        # inutilizable — nadie puede loguearse con password en esta cuenta.
        # El email ya viene verificado por Google, asi que is_verified=True.
        user = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            is_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    elif not user.is_active:
        return RedirectResponse(url=f"{app_redirect}?error=inactive_account", status_code=303)

    redirect_response = RedirectResponse(url="about:blank", status_code=303)
    access_token, refresh_token = await _issue_session(db, redirect_response, request, user)
    redirect_response.headers["location"] = f"{app_redirect}?access_token={access_token}&refresh_token={refresh_token}"
    return redirect_response

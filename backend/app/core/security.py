import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # bcrypt hashes start with $2b$ or $2a$
    if hashed_password.startswith("$2"):
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    # Legacy SHA256 format: salt$hash — supports existing accounts transparently
    try:
        salt, hash_value = hashed_password.split("$", 1)
        computed = hashlib.sha256((plain_password + salt).encode()).hexdigest()
        return secrets.compare_digest(computed, hash_value)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    from app.config import settings

    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    to_encode["iat"] = now
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def get_user_id_from_request(request) -> str | None:
    from app.config import settings

    token = request.cookies.get(settings.JWT_COOKIE_NAME)
    if not token:
        return None
    payload = decode_access_token(token)
    if payload is None:
        return None
    return payload.get("sub")


def decode_access_token(token: str) -> dict | None:
    from app.config import settings

    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None

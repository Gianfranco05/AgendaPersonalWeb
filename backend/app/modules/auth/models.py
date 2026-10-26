from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    # No bloquea el login: la SPA lo usa para mostrar un aviso hasta confirmar.
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    # Version de Terminos/Privacidad aceptada (ver settings.CURRENT_TERMS_VERSION).
    # None = nunca acepto nada (cuenta nueva, o cuenta de antes de que existiera
    # este campo). Si no coincide con la version actual, el cliente tiene que
    # mostrar el gate de aceptacion antes de dejar usar el resto de la app.
    terms_accepted_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    terms_accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Cuando la persona declaro tener 16 anios o mas (edad minima de los
    # Terminos). Se guarda la PRIMERA declaracion y no se pisa en aceptaciones
    # posteriores. None = todavia no la declaro (cuenta de Google nueva o cuenta
    # anterior a este campo): el cliente muestra el gate hasta que la confirme.
    age_confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self):
        return f"<User {self.email}>"


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        index=True,
    )
    # Solo se guarda el sha256 del token: si se filtra la tabla, los tokens
    # siguen sin ser usables. El valor crudo lo tiene unicamente el cliente.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    device_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @property
    def is_active(self) -> bool:
        if self.revoked_at is not None:
            return False
        # SQLite devuelve datetimes naive aunque la columna sea timezone=True;
        # normalizamos a UTC para que la comparacion no explote.
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires > datetime.now(timezone.utc)

    def __repr__(self):
        return f"<RefreshToken user={self.user_id} active={self.is_active}>"


class VerificationPurpose:
    EMAIL_VERIFY = "email_verify"
    PASSWORD_RESET = "password_reset"


class VerificationToken(Base):
    """Token de un solo uso para confirmar email o restablecer contraseña.

    Una sola tabla para ambos casos, discriminada por `purpose`: el ciclo de vida
    (emitir -> usar una vez -> vencer) es identico y no justifica dos tablas.
    """

    __tablename__ = "verification_tokens"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    purpose: Mapped[str] = mapped_column(String(20), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    @property
    def is_usable(self) -> bool:
        if self.used_at is not None:
            return False
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires > datetime.now(timezone.utc)

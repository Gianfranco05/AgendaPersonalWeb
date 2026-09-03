"""Guardas de configuracion de produccion.

`Settings()` lee del entorno al construirse, asi que estos tests instancian
la clase directo (no monkeypatchean el singleton `settings` ya construido) —
monkeypatchear un atributo despues de instanciar no dispara el validator.
"""
import pytest
from pydantic import ValidationError

from app.config import Settings

STRONG_SECRET = "a" * 40


def _base_kwargs(**overrides):
    kwargs = dict(
        ENVIRONMENT="production",
        SECRET_KEY=STRONG_SECRET,
        DEBUG=False,
        DATABASE_URL="postgresql+asyncpg://u:p@host/db",
        RESEND_API_KEY="re_test_key",
    )
    kwargs.update(overrides)
    return kwargs


def test_production_requires_a_strong_secret_key():
    with pytest.raises(ValidationError, match="SECRET_KEY inseguro"):
        Settings(**_base_kwargs(SECRET_KEY="change-this-in-production"))


def test_production_requires_debug_false():
    with pytest.raises(ValidationError, match="DEBUG debe ser false"):
        Settings(**_base_kwargs(DEBUG=True))


def test_production_rejects_sqlite():
    with pytest.raises(ValidationError, match="no puede ser SQLite"):
        Settings(**_base_kwargs(DATABASE_URL="sqlite+aiosqlite:///./x.db"))


def test_production_requires_resend_api_key():
    # Sin esto, send_email() cae al fallback de dev que loguea el link de
    # verificacion/reset (con el token) en texto plano.
    with pytest.raises(ValidationError, match="RESEND_API_KEY"):
        Settings(**_base_kwargs(RESEND_API_KEY=""))


def test_production_passes_with_valid_config():
    settings = Settings(**_base_kwargs())
    assert settings.is_production is True


def test_guards_do_not_apply_outside_production():
    # Los mismos valores "inseguros" son validos en dev/self-hosted.
    settings = Settings(
        ENVIRONMENT="development",
        SECRET_KEY="change-this-in-production",
        DEBUG=True,
        DATABASE_URL="sqlite+aiosqlite:///./x.db",
        RESEND_API_KEY="",
    )
    assert settings.is_production is False

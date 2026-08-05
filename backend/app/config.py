from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRETS = {
    "change-this-in-production",
    "change-this-to-a-random-secret-key-in-production",
    "secret",
    "changeme",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    ENVIRONMENT: str = "development"  # development | production

    DATABASE_URL: str = "sqlite+aiosqlite:///./vida_personal.db"
    SECRET_KEY: str = "change-this-in-production"

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    JWT_COOKIE_NAME: str = "vida_token"

    DEBUG: bool = True
    APP_NAME: str = "Vida Personal"
    APP_VERSION: str = "1.0.0"

    ALLOWED_ORIGINS: str = (
        "http://localhost:8000,http://127.0.0.1:8000,"
        "http://localhost:5173,http://127.0.0.1:5173"
    )

    # Rate limiting (auth endpoints)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_MAX_ATTEMPTS: int = 20
    RATE_LIMIT_WINDOW_SECONDS: int = 300

    # Content-Security-Policy for HTML responses. Empty = disabled.
    # Example: "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    CONTENT_SECURITY_POLICY: str = ""

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10485760

    # Google OAuth (optional — leave empty to disable Google Calendar integration)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/ajustes/google/callback"

    # A donde redirigir tras el callback de Google OAuth. Vacio = ruta relativa
    # (correcto en prod, donde nginx sirve frontend y backend desde el mismo origen).
    # En dev local (frontend y backend en puertos distintos) hay que setear esto a
    # http://localhost:5173 para volver a la SPA en vez de quedarse en el backend.
    FRONTEND_URL: str = ""

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @model_validator(mode="after")
    def _guard_production(self) -> "Settings":
        if self.is_production:
            if self.SECRET_KEY in _INSECURE_SECRETS or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY inseguro para producción. Generá uno con: "
                    'python -c "import secrets; print(secrets.token_hex(32))"'
                )
            if self.DEBUG:
                raise ValueError("DEBUG debe ser false en producción (ENVIRONMENT=production).")
        return self


settings = Settings()

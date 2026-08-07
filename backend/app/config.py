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
    # Access token corto: si se filtra, expira rapido y la revocacion de la
    # sesion (borrar el refresh token) tarda a lo sumo esto en hacerse efectiva.
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_COOKIE_NAME: str = "vida_token"

    # Refresh token: vida larga, revocable, rotado en cada uso.
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    REFRESH_COOKIE_NAME: str = "vida_refresh"

    # Flujo HTML/Jinja2 (legacy): no tiene forma de refrescar el access token
    # — resuelve el usuario con get_user_id_from_request() en cada ruta, sin
    # interceptor. Mantiene el TTL largo que ya tenia para no deslogear cada
    # 15 min. Se elimina cuando la Fase 4 retire las rutas HTML.
    LEGACY_HTML_SESSION_EXPIRE_MINUTES: int = 1440  # 24 horas

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

    # Vacio = limiter en memoria (alcanza con una sola instancia de backend).
    # Con mas de una instancia hace falta Redis: si no, cada proceso cuenta por
    # separado y el limite efectivo se multiplica por la cantidad de replicas.
    REDIS_URL: str = ""

    # Content-Security-Policy for HTML responses. Empty = disabled.
    # Example: "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    CONTENT_SECURITY_POLICY: str = ""

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10485760

    # Email transaccional (Resend). Sin API key los mails se loguean en vez de
    # enviarse — asi dev y tests funcionan sin red ni cuenta.
    RESEND_API_KEY: str = ""
    MAIL_FROM: str = "no-reply@localhost"
    MAIL_FROM_NAME: str = "Vida Personal"
    # Base publica para armar los links de los mails (verificacion, reset).
    PUBLIC_BASE_URL: str = "http://localhost:5173"

    EMAIL_VERIFY_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 1

    # Billing (Stripe). Vacio = billing deshabilitado: todos quedan en plan free
    # y los endpoints de checkout/portal devuelven 503 en vez de romper.
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID_PRO: str = ""
    # A donde vuelve el usuario despues de pagar o de salir del portal.
    BILLING_SUCCESS_URL: str = ""
    BILLING_CANCEL_URL: str = ""

    @property
    def billing_enabled(self) -> bool:
        return bool(self.STRIPE_SECRET_KEY and self.STRIPE_PRICE_ID_PRO)

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
            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError(
                    "DATABASE_URL no puede ser SQLite en producción. Usá Postgres "
                    "(ver docker-compose.prod.yml, servicio `db`)."
                )
        return self


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    DATABASE_URL: str = "sqlite+aiosqlite:///./vida_personal.db"
    SECRET_KEY: str = "change-this-in-production"

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    JWT_COOKIE_NAME: str = "vida_token"

    DEBUG: bool = True
    APP_NAME: str = "Vida Personal"
    APP_VERSION: str = "1.0.0"

    ALLOWED_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10485760

    # Google OAuth (optional — leave empty to disable Google Calendar integration)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/ajustes/google/callback"


settings = Settings()

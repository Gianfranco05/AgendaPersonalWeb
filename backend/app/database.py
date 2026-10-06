from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings


def engine_kwargs(database_url: str) -> dict[str, Any]:
    """Pool y connect_args segun el motor.

    StaticPool es UNA sola conexion compartida por todas las sesiones: solo
    sirve (y hace falta) para SQLite, donde el archivo/memoria es de un unico
    hilo. Con Postgres/asyncpg compartir una conexion entre requests
    concurrentes da "another operation is in progress" y mezcla las
    transacciones (el commit de una request commitea lo a medias de otra), asi
    que ahi se usa el pool normal.
    """
    if "sqlite" in database_url:
        return {
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        }
    return {
        # Detecta conexiones cortadas (reinicio de Postgres, timeout de red)
        # antes de usarlas, en vez de fallar la primera request despues.
        "pool_pre_ping": True,
        # Cada worker de gunicorn tiene su propio pool: con 2*CPU+1 workers el
        # default (5 + 10 de overflow) pasa facil los 100 max_connections de
        # Postgres.
        "pool_size": 5,
        "max_overflow": 5,
    }


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    **engine_kwargs(settings.DATABASE_URL),
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

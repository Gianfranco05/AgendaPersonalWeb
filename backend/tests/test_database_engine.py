"""Pool de conexiones segun el motor.

StaticPool (una sola conexion compartida) solo es valido para SQLite. Con
Postgres, requests concurrentes compartiendo la conexion de asyncpg dan
"another operation is in progress" y mezclan transacciones.
"""

from sqlalchemy.pool import AsyncAdaptedQueuePool, StaticPool

from app.database import engine_kwargs


def test_sqlite_usa_static_pool():
    kwargs = engine_kwargs("sqlite+aiosqlite:///./x.db")
    assert kwargs["poolclass"] is StaticPool
    assert kwargs["connect_args"] == {"check_same_thread": False}


def test_postgres_no_usa_static_pool():
    kwargs = engine_kwargs("postgresql+asyncpg://u:p@db:5432/x")
    assert "poolclass" not in kwargs  # default de create_async_engine: QueuePool
    assert kwargs["pool_pre_ping"] is True
    assert kwargs["pool_size"] + kwargs["max_overflow"] <= 10


def test_postgres_engine_real_tiene_pool_con_varias_conexiones():
    from sqlalchemy.ext.asyncio import create_async_engine

    url = "postgresql+asyncpg://u:p@localhost:5432/x"
    eng = create_async_engine(url, **engine_kwargs(url))
    assert isinstance(eng.pool, AsyncAdaptedQueuePool)
    assert not isinstance(eng.pool, StaticPool)

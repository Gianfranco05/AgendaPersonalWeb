import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from app.config import settings
from app.core.base import Base
from app.modules.auth.models import User
from app.modules.finanzas.models import Transaction, Category, BankAccount, Budget
from app.modules.anotaciones.models import Note, Tag, note_tags
from app.modules.eventos.models import Event


async def init_db():
    engine = create_async_engine(settings.DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("Base de datos creada exitosamente!")


if __name__ == "__main__":
    asyncio.run(init_db())

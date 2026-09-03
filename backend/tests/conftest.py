import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_db
from app.core.http_security import auth_rate_limiter, billing_rate_limiter
from app.core.base import Base
from app.core.security import hash_password
from app.modules.auth.models import User
from app.modules.finanzas.models import Category, Transaction
from app.modules.anotaciones.models import Note

TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest_asyncio.fixture(autouse=True)
async def _reset_rate_limiter():
    # The limiter is process-global; without this, logins accumulate across tests
    auth_rate_limiter.reset()
    billing_rate_limiter.reset()
    yield


@pytest_asyncio.fixture(scope="function")
async def engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session):
    user = User(
        id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        email="test@test.com",
        password_hash=hash_password("test123"),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture(scope="function")
async def client(engine, db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def auth_client(client, test_user):
    await client.post("/auth/login", data={
        "email": "test@test.com",
        "password": "test123",
    })
    return client


@pytest_asyncio.fixture(scope="function")
async def api_auth_client(client, test_user):
    await client.post("/auth/api/login", json={
        "email": "test@test.com",
        "password": "test123",
    })
    return client


@pytest_asyncio.fixture(scope="function")
async def test_category(db_session, test_user):
    category = Category(
        id="c1c2c3c4-c5c6-c7c8-c9ca-cbcccdcecfd0",
        user_id=test_user.id,
        name="Alimentacion",
        color="#10B981",
        icon="utensils",
    )
    db_session.add(category)
    await db_session.commit()
    return category


@pytest_asyncio.fixture
async def seed_transactions(request, db_session, test_user):
    count = getattr(request, "param", 5)
    types = ["income", "expense"]
    amounts = [1000, 2500, 500, 15000, 750, 3200, 180, 9990, 450, 12000]
    dates = ["2025-01-15", "2025-02-20", "2025-03-10", "2025-04-05", "2025-05-25",
             "2025-06-01", "2025-06-15", "2025-07-04", "2025-08-30", "2025-09-12"]
    merchants = ["", "Jumbo", "Disco", "Coto", "MercadoLibre", "Netflix", "Spotify", ""]
    methods = ["cash", "debit_card", "credit_card", "transfer"]
    accounts = ["cash", "checking", "savings"]
    txn_ids = []
    for i in range(count):
        t = Transaction(
            user_id=test_user.id,
            amount=amounts[i % len(amounts)],
            type=types[i % 2],
            transaction_date=dates[i % len(dates)],
            product_name=f"Producto {i + 1}",
            merchant_name=merchants[i % len(merchants)],
            payment_method=methods[i % len(methods)],
            account_type=accounts[i % 3],
            notes=f"Nota de transacción {i + 1}" if i % 3 == 0 else None,
        )
        db_session.add(t)
        txn_ids.append(t.id)
    await db_session.commit()
    return txn_ids


@pytest_asyncio.fixture
async def seed_notes(request, db_session, test_user):
    count = getattr(request, "param", 5)
    titles = ["Idea", "Lista compras", "Diario", "Recordatorio", "Meta",
              "Libro", "Pelicula", "Proyecto", "Receta", "Idea viaje"]
    colors = ["#ffffff", "#ff0000", "#00ff00", "#0000ff", "#ffff00"]
    note_ids = []
    for i in range(count):
        n = Note(
            user_id=test_user.id,
            title=f"{titles[i % len(titles)]} {i + 1}",
            content=f"Contenido de la nota número {i + 1}. " * 3,
            is_pinned=i == 0,
            is_archived=i > count - 3,
            color=colors[i % len(colors)],
        )
        db_session.add(n)
        note_ids.append(n.id)
    await db_session.commit()
    return note_ids

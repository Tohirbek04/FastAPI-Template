import os

os.environ["ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://app:app@localhost:5435/app_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6380/0")

from collections.abc import AsyncIterator, Awaitable, Callable  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db import registry  # noqa: E402, F401
from app.db.base import Base  # noqa: E402
from app.users.models import User  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)


@pytest.fixture(scope="session", autouse=True)
async def _create_test_database() -> None:
    """Create the app_test database if it does not exist."""
    admin_url = get_settings().database_url.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        exists = await conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = 'app_test'"))
        if not exists:
            await conn.execute(text("CREATE DATABASE app_test"))
    await admin_engine.dispose()


@pytest.fixture(scope="session")
async def engine(_create_test_database: None) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Run each test inside a savepoint that is rolled back afterwards."""
    async with engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(
            bind=conn,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        yield session
        await session.close()
        await conn.rollback()


@pytest.fixture
def user_factory(
    db_session: AsyncSession,
) -> Callable[..., Awaitable[User]]:
    async def _create(
        email: str = "user@example.com",
        password: str = "password123",
        **kwargs: Any,
    ) -> User:
        user = User(email=email, hashed_password=hash_password(password), **kwargs)
        db_session.add(user)
        await db_session.flush()
        return user

    return _create


from httpx import ASGITransport, AsyncClient  # noqa: E402


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    from app.db.session import get_db
    from app.main import app

    async def _get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()

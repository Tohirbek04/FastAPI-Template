import pytest
from app.core.config import get_settings
from app.users.models import User
from scripts.seed import seed
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


async def test_seed_creates_superuser_once(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FIRST_SUPERUSER_EMAIL", "root@example.com")
    monkeypatch.setenv("FIRST_SUPERUSER_PASSWORD", "rootpassword123")
    get_settings.cache_clear()
    try:
        await seed()
        await seed()  # idempotent — the second call must be a no-op

        async with AsyncSession(engine) as session:
            from app.users.repository import UserRepository

            user = await UserRepository(session).get_by_email("root@example.com")
            assert user is not None
            assert user.is_superuser
            # cleanup — seed() commits for real
            await session.execute(delete(User).where(User.email == "root@example.com"))
            await session.commit()
    finally:
        get_settings.cache_clear()

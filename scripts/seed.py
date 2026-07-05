import asyncio

import structlog
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.db.session import SessionFactory
from app.users.repository import UserRepository

logger = structlog.get_logger()


async def seed() -> None:
    settings = get_settings()
    if not settings.first_superuser_email or not settings.first_superuser_password:
        logger.warning("seed_skipped", reason="FIRST_SUPERUSER_* env not set")
        return
    async with SessionFactory() as session:
        repo = UserRepository(session)
        if await repo.get_by_email(settings.first_superuser_email):
            logger.info("superuser_exists", email=settings.first_superuser_email)
            return
        await repo.create(
            email=settings.first_superuser_email,
            hashed_password=hash_password(settings.first_superuser_password),
            is_superuser=True,
        )
        await session.commit()
        logger.info("superuser_created", email=settings.first_superuser_email)


if __name__ == "__main__":
    configure_logging()
    asyncio.run(seed())

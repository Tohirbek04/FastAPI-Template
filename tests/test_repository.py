import uuid

from app.users.repository import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession


async def test_create_and_get(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = await repo.create(email="a@example.com", hashed_password="x")
    assert user.id is not None

    found = await repo.get(user.id)
    assert found is not None
    assert found.email == "a@example.com"


async def test_get_by_email(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    await repo.create(email="b@example.com", hashed_password="x")

    assert (await repo.get_by_email("b@example.com")) is not None
    assert (await repo.get_by_email("missing@example.com")) is None


async def test_update_and_delete(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = await repo.create(email="c@example.com", hashed_password="x")

    updated = await repo.update(user, full_name="New Name")
    assert updated.full_name == "New Name"

    await repo.delete(user)
    assert (await repo.get(user.id)) is None


async def test_get_missing_returns_none(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    assert (await repo.get(uuid.uuid4())) is None

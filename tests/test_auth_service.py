import pytest
from app.auth.service import AuthService
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import decode_token
from sqlalchemy.ext.asyncio import AsyncSession


async def test_register_creates_user(db_session: AsyncSession) -> None:
    user = await AuthService(db_session).register("new@example.com", "password123")
    assert user.email == "new@example.com"
    assert user.hashed_password != "password123"


async def test_register_duplicate_email_conflicts(db_session: AsyncSession) -> None:
    service = AuthService(db_session)
    await service.register("dup@example.com", "password123")
    with pytest.raises(ConflictError):
        await service.register("dup@example.com", "password123")


async def test_login_returns_token_pair(db_session: AsyncSession) -> None:
    service = AuthService(db_session)
    user = await service.register("login@example.com", "password123")

    pair = await service.login("login@example.com", "password123")

    assert decode_token(pair.access_token, "access")["sub"] == str(user.id)
    assert decode_token(pair.refresh_token, "refresh")["sub"] == str(user.id)


async def test_login_wrong_password_unauthorized(db_session: AsyncSession) -> None:
    service = AuthService(db_session)
    await service.register("wrong@example.com", "password123")
    with pytest.raises(UnauthorizedError):
        await service.login("wrong@example.com", "bad-password")


async def test_refresh_rotates_tokens(db_session: AsyncSession) -> None:
    service = AuthService(db_session)
    await service.register("rot@example.com", "password123")
    pair = await service.login("rot@example.com", "password123")

    new_pair = await service.refresh(pair.refresh_token)

    assert decode_token(new_pair.access_token, "access")


async def test_refresh_with_access_token_rejected(db_session: AsyncSession) -> None:
    service = AuthService(db_session)
    await service.register("mix@example.com", "password123")
    pair = await service.login("mix@example.com", "password123")
    with pytest.raises(UnauthorizedError):
        await service.refresh(pair.access_token)

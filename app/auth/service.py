import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import TokenPair
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.users.models import User
from app.users.repository import UserRepository
from app.users.tasks import send_welcome_email

# Verified even when the user does not exist, so both login paths take
# comparable time — prevents user enumeration via response timing.
_DUMMY_HASH = hash_password("timing-equalization-dummy")


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)

    async def register(self, email: str, password: str, full_name: str = "") -> User:
        if await self.users.get_by_email(email):
            raise ConflictError("Email already registered")
        user = await self.users.create(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        await send_welcome_email.kiq(user.email)
        return user

    async def login(self, email: str, password: str) -> TokenPair:
        user = await self.users.get_by_email(email)
        if user is None:
            verify_password(password, _DUMMY_HASH)
            raise UnauthorizedError("Incorrect email or password")
        if not verify_password(password, user.hashed_password):
            # Same message as the unknown-email case — prevents user enumeration
            raise UnauthorizedError("Incorrect email or password")
        if not user.is_active:
            raise UnauthorizedError("Inactive user")
        return self._token_pair(user.id)

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = decode_token(refresh_token, expected_type="refresh")
        user = await self.users.get(uuid.UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise UnauthorizedError("User not found or inactive")
        return self._token_pair(user.id)

    def _token_pair(self, user_id: uuid.UUID) -> TokenPair:
        return TokenPair(
            access_token=create_token(str(user_id), "access"),
            refresh_token=create_token(str(user_id), "refresh"),
        )

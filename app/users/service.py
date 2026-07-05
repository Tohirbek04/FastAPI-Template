from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = UserRepository(session)

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        values: dict[str, str] = {}
        if data.full_name is not None:
            values["full_name"] = data.full_name
        if data.password is not None:
            values["hashed_password"] = hash_password(data.password)
        if values:
            user = await self.repo.update(user, **values)
        return user

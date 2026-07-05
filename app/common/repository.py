import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base


class BaseRepository[ModelT: Base]:
    """Generic CRUD repository over a single model.

    Receives its session explicitly, so it is trivial to swap or mock in
    tests. Methods flush (send SQL) but never commit — the commit decision
    belongs to the request-scoped unit of work in get_db().
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, obj_id: uuid.UUID) -> ModelT | None:
        return await self.session.get(self.model, obj_id)

    async def create(self, **data: Any) -> ModelT:
        obj = self.model(**data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def update(self, obj: ModelT, **data: Any) -> ModelT:
        for key, value in data.items():
            setattr(obj, key, value)
        await self.session.flush()
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()

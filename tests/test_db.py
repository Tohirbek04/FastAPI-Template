from app.db.base import TimestampedBase
from app.db.session import SessionFactory
from sqlalchemy import text


async def test_engine_connects_and_selects() -> None:
    async with SessionFactory() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1


def test_timestamped_base_columns() -> None:
    assert hasattr(TimestampedBase, "id")
    assert hasattr(TimestampedBase, "created_at")
    assert hasattr(TimestampedBase, "updated_at")

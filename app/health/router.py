from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Msg
from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter()


@router.get("", response_model=Msg)
async def health(db: Annotated[AsyncSession, Depends(get_db)]) -> Msg:
    """Genuine liveness check: pings the database and Redis.

    Used by load balancers, container HEALTHCHECKs and post-deploy probes.
    """
    await db.execute(text("SELECT 1"))
    redis: Redis = Redis.from_url(get_settings().redis_url)
    try:
        await redis.ping()
    finally:
        await redis.aclose()
    return Msg(detail="ok")

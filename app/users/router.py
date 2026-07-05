from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser
from app.core.exceptions import PermissionDeniedError
from app.db.session import get_db
from app.users.models import User
from app.users.schemas import UserRead, UserUpdate
from app.users.service import UserService

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def read_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
async def update_me(
    data: UserUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    user = await UserService(db).update_profile(current_user, data)
    return UserRead.model_validate(user)


@router.get("", response_model=Page[UserRead])
async def list_users(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Page[UserRead]:
    if not current_user.is_superuser:
        raise PermissionDeniedError("Superuser required")
    # Doim deterministik order_by — aks holda Postgres tartibi barqaror emas
    return await apaginate(db, select(User).order_by(User.created_at, User.id))

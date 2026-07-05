from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import RefreshRequest, RegisterRequest, TokenPair
from app.auth.service import AuthService
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.users.schemas import UserRead

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(
    request: Request,  # slowapi decorator talab qiladi
    response: Response,  # slowapi headers_enabled uchun shart
    data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    user = await AuthService(db).register(data.email, data.password, data.full_name)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenPair)
@limiter.limit("20/minute")
async def login(
    request: Request,
    response: Response,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    return await AuthService(db).login(form.username, form.password)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    data: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    return await AuthService(db).refresh(data.refresh_token)

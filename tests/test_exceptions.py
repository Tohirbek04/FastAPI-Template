from app.core.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    UnauthorizedError,
    register_exception_handlers,
)
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


def test_error_hierarchy_attrs() -> None:
    assert NotFoundError.status_code == 404
    assert ConflictError.status_code == 409
    assert UnauthorizedError.status_code == 401
    assert PermissionDeniedError.status_code == 403
    err = NotFoundError("User not found")
    assert err.detail == "User not found"
    assert isinstance(err, AppError)


async def test_handler_converts_to_json() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise ConflictError("Email already registered")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/boom")

    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered", "code": "conflict"}

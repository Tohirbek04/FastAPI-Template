from app.core.security import create_token
from app.users.models import User
from httpx import AsyncClient


def auth_header(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_token(str(user.id), 'access')}"}


async def test_me_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


async def test_me_returns_current_user(client: AsyncClient, user_factory) -> None:
    user = await user_factory(email="me@example.com")
    response = await client.get("/api/v1/users/me", headers=auth_header(user))
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


async def test_patch_me_updates_name_and_password(client: AsyncClient, user_factory) -> None:
    user = await user_factory(email="patch@example.com", password="password123")

    response = await client.patch(
        "/api/v1/users/me",
        headers=auth_header(user),
        json={"full_name": "Yangi Ism", "password": "newpassword123"},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Yangi Ism"

    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "patch@example.com", "password": "newpassword123"},
    )
    assert login.status_code == 200


async def test_list_users_forbidden_for_regular(client: AsyncClient, user_factory) -> None:
    user = await user_factory(email="plain@example.com")
    response = await client.get("/api/v1/users", headers=auth_header(user))
    assert response.status_code == 403


async def test_list_users_paginated_for_superuser(client: AsyncClient, user_factory) -> None:
    admin = await user_factory(email="admin@example.com", is_superuser=True)
    for i in range(3):
        await user_factory(email=f"u{i}@example.com")

    response = await client.get(
        "/api/v1/users", headers=auth_header(admin), params={"page": 1, "size": 2}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 4
    assert len(body["items"]) == 2

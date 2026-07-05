from httpx import AsyncClient


async def test_register_login_refresh_flow(client: AsyncClient) -> None:
    # register
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "flow@example.com", "password": "password123"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "flow@example.com"
    assert "hashed_password" not in response.json()

    # duplicate → 409
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "flow@example.com", "password": "password123"},
    )
    assert response.status_code == 409

    # login (OAuth2 form: username field carries the email)
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "flow@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    tokens = response.json()
    assert tokens["token_type"] == "bearer"

    # refresh
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_login_wrong_password_401(client: AsyncClient, user_factory) -> None:
    await user_factory(email="u1@example.com", password="password123")
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "u1@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


async def test_refresh_with_access_token_401(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "u2@example.com", "password": "password123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "u2@example.com", "password": "password123"},
    )
    access = login.json()["access_token"]
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert response.status_code == 401


async def test_short_password_422(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register", json={"email": "u3@example.com", "password": "short"}
    )
    assert response.status_code == 422

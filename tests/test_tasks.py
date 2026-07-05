import structlog
from app.users.tasks import send_welcome_email
from httpx import AsyncClient


async def test_send_welcome_email_logs() -> None:
    with structlog.testing.capture_logs() as logs:
        task = await send_welcome_email.kiq("hello@example.com")
        await task.wait_result(timeout=5)

    assert any(log["event"] == "welcome_email_sent" for log in logs)


async def test_register_enqueues_welcome_email(client: AsyncClient) -> None:
    with structlog.testing.capture_logs() as logs:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "task@example.com", "password": "password123"},
        )

    assert response.status_code == 201
    assert any(log["event"] == "welcome_email_sent" for log in logs)

import structlog

from app.tasks.broker import broker

logger = structlog.get_logger()


@broker.task
async def send_welcome_email(email: str) -> None:
    """Namuna task. Real loyihada bu yerda email provider chaqiriladi.

    Cron misoli:  @broker.task(schedule=[{"cron": "0 3 * * *", "schedule_id": "daily"}])
    """
    logger.info("welcome_email_sent", email=email)

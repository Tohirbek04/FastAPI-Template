import structlog

from app.tasks.broker import broker

logger = structlog.get_logger()


@broker.task
async def send_welcome_email(email: str) -> None:
    """Example task. In a real project this would call an email provider.

    Cron example:  @broker.task(schedule=[{"cron": "0 3 * * *", "schedule_id": "daily"}])
    """
    logger.info("welcome_email_sent", email=email)

"""Celery configuration and app"""

from celery import Celery
from src.core.config.settings import settings

# Create Celery app
celery_app = Celery(
    main=settings.APP_NAME,
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=["json"],
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    broker_connection_retry_on_startup=True,
)


@celery_app.task(name="celery.ping")
def ping():
    """Ping task for testing"""
    return "pong"

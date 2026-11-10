from celery import Celery

from src.config.settings import settings

celery_app = Celery(
    "rpaloop",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["src.services.executor"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

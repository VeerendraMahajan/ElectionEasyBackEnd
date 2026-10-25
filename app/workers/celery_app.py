import os
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "voterlens",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
)

celery_app.autodiscover_tasks(["app.workers.document_tasks"])

import pytest
from app.workers.celery_app import celery_app
from app.workers.document_tasks import process_document_job


def test_celery_task_registration():
    """Verify document processing task is registered in Celery application."""
    assert "app.workers.document_tasks.process_document_job" in celery_app.tasks


def test_celery_app_configuration():
    """Verify Celery task execution, serialization, and timeout settings."""
    conf = celery_app.conf
    assert conf.task_serializer == "json"
    assert conf.result_serializer == "json"
    assert conf.task_acks_late is True
    assert conf.worker_prefetch_multiplier == 1
    assert conf.task_time_limit >= 1800

"""Celery configuration tests."""

from __future__ import annotations

from core.celery_app import celery_app
from core.config import get_settings


def test_celery_acks_late_enabled():
    cfg = get_settings(reload=True)
    assert cfg.celery.task_acks_late is True


def test_celery_app_registered():
    assert "core.tasks.pipeline_tasks.start_pipeline" in celery_app.tasks

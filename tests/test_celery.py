"""Celery configuration tests."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

from core.celery_app import (
    ProgressTask,
    _on_task_failure,
    _on_task_postrun,
    _on_task_prerun,
    _on_task_retry,
    _use_memory_progress,
    celery_app,
    get_redis,
    publish_job_progress,
    publish_progress,
)
from core.config import get_settings


def test_celery_acks_late_enabled():
    cfg = get_settings(reload=True)
    assert cfg.celery.task_acks_late is True


def test_celery_app_registered():
    assert "core.tasks.pipeline_tasks.start_pipeline" in celery_app.tasks


def test_celery_beat_schedule_has_stack_probe():
    assert "probe-stack-health-ops" in celery_app.conf.beat_schedule


def test_use_memory_progress_inprocess(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    assert _use_memory_progress() is True


def test_use_memory_progress_celery(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "celery")
    assert _use_memory_progress() is False


def test_get_redis_inprocess_returns_kv(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    r = get_redis()
    # In-process mode returns MemoryKVStore, not a real Redis client
    assert hasattr(r, "get") and hasattr(r, "set") and hasattr(r, "incr")


def test_publish_progress_inprocess_path(monkeypatch):
    import core.celery_app as ca
    from core.progress_bus import reset_progress_bus, get_progress_bus
    reset_progress_bus()
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    # Patch the module-level cfg used by celery_app so _use_memory_progress() returns True
    monkeypatch.setattr(ca, "cfg", cfg)
    publish_progress("job-inproc-1", stage="ingesting", progress=0.1, skip_timing=True)
    bus = get_progress_bus(cfg)
    snap = bus.get_snapshot(f"{cfg.redis.pubsub_channel_prefix}job-inproc-1")
    assert snap is not None
    assert "ingesting" in snap


def test_publish_job_progress_inprocess_path(monkeypatch):
    import core.celery_app as ca
    from core.progress_bus import reset_progress_bus, get_progress_bus
    reset_progress_bus()
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    monkeypatch.setattr(ca, "cfg", cfg)
    publish_job_progress("pj-inproc-1", stage="uploading", progress=0.5)
    bus = get_progress_bus(cfg)
    snap = bus.get_snapshot(f"{cfg.redis.publish_pubsub_channel_prefix}pj-inproc-1")
    assert snap is not None
    assert "uploading" in snap


def test_on_task_prerun_logs():
    mock_task = MagicMock()
    mock_task.name = "test.task"
    _on_task_prerun(task_id="tid1", task=mock_task)  # no exception = pass


def test_on_task_postrun_logs():
    mock_task = MagicMock()
    mock_task.name = "test.task"
    _on_task_postrun(task_id="tid2", task=mock_task, state="SUCCESS")


def test_on_task_retry_logs():
    _on_task_retry(task_id="tid3", reason="timeout")


def test_on_task_failure_no_sentry(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.observability, "sentry_dsn", "")
    mock_task = MagicMock()
    mock_task.name = "test.task"
    _on_task_failure(
        task_id="tid4",
        exception=RuntimeError("boom"),
        task=mock_task,
        traceback=None,
        einfo=None,
    )


def test_on_task_failure_sentry_missing_module(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.observability, "sentry_dsn", "https://x@sentry.io/1")
    mock_task = MagicMock()
    mock_task.name = "test.task"
    # Remove sentry_sdk if present
    with patch.dict(sys.modules, {"sentry_sdk": None}):
        _on_task_failure(
            task_id="tid5",
            exception=RuntimeError("boom"),
            task=mock_task,
            traceback=None,
            einfo=None,
        )


def test_on_task_failure_sentry_captures(monkeypatch):
    import core.celery_app as ca
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.observability, "sentry_dsn", "https://x@sentry.io/1")
    # Patch module-level cfg so the signal handler sees the DSN
    monkeypatch.setattr(ca, "cfg", cfg)
    mock_task = MagicMock()
    mock_task.name = "test.task"
    captured: list[Exception] = []
    fake_sentry = types.ModuleType("sentry_sdk")
    fake_sentry.capture_exception = lambda exc: captured.append(exc)
    with patch.dict(sys.modules, {"sentry_sdk": fake_sentry}):
        ca._on_task_failure(
            task_id="tid6",
            exception=RuntimeError("sentry-test"),
            task=mock_task,
            traceback=None,
            einfo=None,
        )
    assert len(captured) == 1
    assert "sentry-test" in str(captured[0])


def test_init_worker_sentry_no_dsn(monkeypatch):
    from core import celery_app as ca
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.observability, "sentry_dsn", "")
    ca._init_worker_sentry()  # should be a no-op


def test_progress_task_report_calls_publish(monkeypatch):
    import core.celery_app as ca
    from core.progress_bus import reset_progress_bus, get_progress_bus
    reset_progress_bus()
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    monkeypatch.setattr(ca, "cfg", cfg)
    task = ProgressTask()
    task.report("job-task-r", stage="detecting", progress=0.4)
    snap = get_progress_bus(cfg).get_snapshot(
        f"{cfg.redis.pubsub_channel_prefix}job-task-r"
    )
    assert snap is not None
    assert "detecting" in snap

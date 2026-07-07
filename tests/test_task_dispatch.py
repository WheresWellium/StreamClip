"""Tests for task dispatch seam (ADR-001 4.2)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from core.celery_app import celery_app
from core.config import get_settings
from core import task_dispatch as td
from core.inprocess_worker import start_inprocess_worker, stop_inprocess_worker
from core.progress_bus import reset_progress_bus

# Non-pipeline tasks routed through the dispatch seam (MASTER_TODO §4.17) —
# all must be resolvable by name once the in-process worker has started.
ROUTED_TASK_NAMES = (
    "core.tasks.publish_tasks.publish_to_platform",
    "core.tasks.publish_tasks.process_due_scheduled_jobs",
    "core.tasks.vault_tasks.copy_clip_to_vault",
    "core.tasks.notify_tasks.send_bug_report_email",
    "core.tasks.notify_tasks.send_license_key_email",
    "core.tasks.notify_tasks.export_training_bundle",
)


@pytest.fixture(autouse=True)
def _reset_inprocess_runtime():
    stop_inprocess_worker(wait=False)
    reset_progress_bus()
    yield
    stop_inprocess_worker(wait=True)
    reset_progress_bus()


def test_dispatch_task_uses_celery_by_default(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "celery")
    task = MagicMock()
    task.apply_async.return_value = MagicMock(id="task-abc")
    handle = td.dispatch_task(task, args=("j1",), cfg=cfg)
    assert handle.id == "task-abc"
    task.apply_async.assert_called_once()


def test_dispatch_task_inprocess_submits_to_worker(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")

    calls: list[str] = []

    @celery_app.task(name="tests.dispatch.echo")
    def echo_task(job_id: str) -> str:
        calls.append(job_id)
        return job_id

    handle = td.dispatch_task(echo_task, args=("j1",), cfg=cfg)
    assert handle.id

    deadline = time.time() + 5
    while time.time() < deadline and not calls:
        time.sleep(0.05)
    assert calls == ["j1"]


def test_dispatch_task_by_name_inprocess(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")

    calls: list[str] = []

    @celery_app.task(name="tests.dispatch.by_name")
    def by_name_task(value: str) -> str:
        calls.append(value)
        return value

    handle = td.dispatch_task_by_name("tests.dispatch.by_name", args=("a@b.com",), cfg=cfg)
    assert handle.id

    deadline = time.time() + 5
    while time.time() < deadline and not calls:
        time.sleep(0.05)
    assert calls == ["a@b.com"]


def test_dispatch_task_by_name_celery_uses_send_task(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "celery")

    with patch.object(celery_app, "send_task", return_value=MagicMock(id="ct-1")) as send:
        handle = td.dispatch_task_by_name(
            "core.tasks.notify_tasks.send_license_key_email",
            args=("buyer@test.local", "SCPRO-KEY", None),
            queue="default",
            cfg=cfg,
        )
    assert handle.id == "ct-1"
    args, kwargs = send.call_args
    assert args[0] == "core.tasks.notify_tasks.send_license_key_email"
    assert kwargs["args"] == ("buyer@test.local", "SCPRO-KEY", None)
    assert kwargs["queue"] == "default"


def test_inprocess_worker_registers_routed_tasks(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    monkeypatch.setattr(cfg.queue, "inprocess_beat", False)

    start_inprocess_worker(cfg)
    for name in ROUTED_TASK_NAMES:
        assert name in celery_app.tasks, f"task not registered for in-process mode: {name}"


def test_dispatch_routed_task_by_name_inprocess(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    monkeypatch.setattr(cfg.queue, "inprocess_beat", False)

    worker = start_inprocess_worker(cfg)
    with patch.object(worker, "submit_by_name", return_value="tid-1") as submit:
        handle = td.dispatch_task_by_name(
            "core.tasks.vault_tasks.copy_clip_to_vault",
            args=("vc-1", "clips/final.mp4", None),
            cfg=cfg,
        )
    assert handle.id == "tid-1"
    submit.assert_called_once_with(
        "core.tasks.vault_tasks.copy_clip_to_vault",
        args=("vc-1", "clips/final.mp4", None),
        kwargs={},
        queue=None,
    )

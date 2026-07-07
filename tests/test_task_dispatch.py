"""Tests for task dispatch seam (ADR-001 4.2)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from core.celery_app import celery_app
from core.config import get_settings
from core import task_dispatch as td
from core.inprocess_worker import stop_inprocess_worker
from core.progress_bus import reset_progress_bus


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

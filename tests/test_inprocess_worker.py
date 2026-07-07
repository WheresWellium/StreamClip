"""Tests for in-process worker, task runner, and memory progress bus (ADR-001 §4.2)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from celery import chain, group

from core.celery_app import celery_app, publish_progress
from core.config import get_settings
from core import inprocess_worker as ipw_mod
from core.inprocess_worker import InProcessWorker, start_inprocess_worker, stop_inprocess_worker
from core.progress_bus import get_progress_bus, reset_progress_bus
from core import task_runner


@pytest.fixture(autouse=True)
def _reset_runtime():
    stop_inprocess_worker(wait=False)
    reset_progress_bus()
    yield
    stop_inprocess_worker(wait=False)
    reset_progress_bus()


def test_memory_progress_publish_without_redis(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")

    publish_progress("job-mem", stage="ingesting", progress=0.1, message="hello")

    bus = get_progress_bus(cfg)
    channel = f"{cfg.redis.pubsub_channel_prefix}job-mem"
    snapshot = bus.get_snapshot(channel)
    assert snapshot is not None
    assert "ingesting" in snapshot
    assert '"event_id": 1' in snapshot or '"event_id":1' in snapshot.replace(" ", "")


def test_inprocess_worker_runs_mock_task():
    cfg = get_settings(reload=True)
    worker = InProcessWorker(cfg)

    calls: list[tuple] = []

    @celery_app.task(name="tests.inprocess.echo")
    def echo_task(value: str) -> str:
        calls.append((value,))
        return value

    try:
        future = worker._submit_callable(echo_task, ("hi",), {})
        assert future.result(timeout=5) == "hi"
        assert calls == [("hi",)]
    finally:
        worker.shutdown()


def test_inprocess_chain_execution():
    cfg = get_settings(reload=True)
    worker = InProcessWorker(cfg)
    order: list[str] = []

    @celery_app.task(name="tests.inprocess.step_a")
    def step_a(job_id: str) -> str:
        order.append("a")
        return job_id

    @celery_app.task(name="tests.inprocess.step_b")
    def step_b(job_id: str) -> str:
        order.append("b")
        return job_id

    try:
        workflow = chain(step_a.si("j1"), step_b.si("j1"))
        worker.execute_work(workflow)
        assert order == ["a", "b"]
    finally:
        worker.shutdown()


def test_inprocess_group_parallel():
    cfg = get_settings(reload=True)
    worker = InProcessWorker(cfg)
    seen: list[int] = []

    @celery_app.task(name="tests.inprocess.add_one")
    def add_one(n: int) -> int:
        seen.append(n)
        return n + 1

    try:
        workflow = group(add_one.s(1), add_one.s(2), add_one.s(3))
        results = worker.execute_work(workflow)
        assert sorted(results) == [2, 3, 4]
        assert sorted(seen) == [1, 2, 3]
    finally:
        worker.shutdown()


def test_task_runner_apply_async_inprocess(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    start_inprocess_worker(cfg)

    ran: list[str] = []

    @celery_app.task(name="tests.inprocess.runner_task")
    def runner_task(job_id: str) -> str:
        ran.append(job_id)
        return job_id

    sig = runner_task.si("job-runner")
    result = task_runner.apply_async(sig)
    assert result.id

    deadline = time.time() + 5
    while time.time() < deadline and not ran:
        time.sleep(0.05)
    assert ran == ["job-runner"]


def test_task_runner_uses_celery_when_configured(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "celery")

    mock_sig = MagicMock()
    mock_sig.apply_async.return_value = MagicMock(id="celery-id")

    result = task_runner.apply_async(mock_sig, queue="default")
    assert result.id == "celery-id"
    mock_sig.apply_async.assert_called_once_with(queue="default")


def test_task_runner_delay_uses_celery_when_configured(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "celery")

    mock_task = MagicMock()
    mock_task.delay.return_value = MagicMock(id="celery-delay-id")

    result = task_runner.delay(mock_task, "pj-1")
    assert result.id == "celery-delay-id"
    mock_task.delay.assert_called_once_with("pj-1")


def test_inprocess_beat_fires_schedule_entries(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(ipw_mod, "_BEAT_TICK_SECS", 0.05)

    fired: list[float] = []

    @celery_app.task(name="tests.inprocess.beat_tick")
    def beat_tick() -> None:
        fired.append(time.time())

    monkeypatch.setattr(
        celery_app.conf,
        "beat_schedule",
        {"test-tick": {"task": "tests.inprocess.beat_tick", "schedule": 0.1}},
    )

    worker = InProcessWorker(cfg)
    try:
        deadline = time.time() + 5
        while time.time() < deadline and not fired:
            time.sleep(0.05)
        assert fired, "beat entry never fired in-process"
    finally:
        worker.shutdown()


def test_inprocess_beat_disabled_by_config(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "inprocess_beat", False)

    worker = InProcessWorker(cfg)
    try:
        assert worker._beat_thread is None
    finally:
        worker.shutdown()


def test_start_worker_registers_task_modules(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "inprocess_beat", False)

    start_inprocess_worker(cfg)
    for name in (
        "core.tasks.publish_tasks.publish_to_platform",
        "core.tasks.vault_tasks.copy_clip_to_vault",
        "core.tasks.notify_tasks.send_bug_report_email",
    ):
        assert name in celery_app.tasks

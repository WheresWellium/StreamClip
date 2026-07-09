"""Tests for in-process worker, task runner, and memory progress bus (ADR-001 §4.2)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from celery import chain, chord, group

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


def test_task_runner_delay_inprocess(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    worker = MagicMock()
    worker.submit_task.return_value = "ip-delay-1"
    with patch.object(task_runner, "get_worker", return_value=None), patch.object(
        task_runner, "start_inprocess_worker", return_value=worker,
    ) as start, patch.object(task_runner, "get_settings", return_value=cfg):
        result = task_runner.delay(MagicMock(name="t"), "pj-2", force=True)
    assert result.id == "ip-delay-1"
    start.assert_called_once_with(cfg)
    worker.submit_task.assert_called_once()
    call_kwargs = worker.submit_task.call_args.kwargs
    assert call_kwargs["args"] == ("pj-2",)
    assert call_kwargs["kwargs"] == {"force": True}


def test_task_runner_apply_async_inprocess_starts_worker(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    worker = MagicMock()
    worker.submit_canvas.return_value = MagicMock(id="canvas-1")
    with patch.object(task_runner, "get_worker", return_value=None), patch.object(
        task_runner, "start_inprocess_worker", return_value=worker,
    ), patch.object(task_runner, "get_settings", return_value=cfg):
        result = task_runner.apply_async(MagicMock(), queue="default")
    assert result.id == "canvas-1"
    worker.submit_canvas.assert_called_once()


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
        "core.tasks.notify_tasks.send_ops_webhook",
        "core.tasks.notify_tasks.send_job_failed_ops_alert",
        "core.tasks.notify_tasks.probe_stack_health_ops_alert",
    ):
        assert name in celery_app.tasks


def test_start_inprocess_worker_is_singleton(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "inprocess_beat", False)
    stop_inprocess_worker()
    first = start_inprocess_worker(cfg)
    second = start_inprocess_worker(cfg)
    assert first is second
    stop_inprocess_worker()


def test_resolve_task_unknown_name_raises(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "inprocess_beat", False)
    worker = InProcessWorker(cfg)
    try:
        with pytest.raises(KeyError):
            worker._resolve_task("tests.inprocess.does_not_exist")
    finally:
        worker.shutdown()


def test_route_queue_gpu_task_name(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "inprocess_beat", False)
    worker = InProcessWorker(cfg)
    try:
        assert worker._route_queue("core.tasks.pipeline_tasks.process_clip") == "gpu"
        assert worker._route_queue("anything", explicit="default") == "default"
    finally:
        worker.shutdown()


def test_inprocess_chord_runs_callback(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "inprocess_beat", False)
    worker = InProcessWorker(cfg)
    seen: list[object] = []

    @celery_app.task(name="tests.inprocess.chord_header")
    def chord_header(n: int) -> int:
        return n * 2

    @celery_app.task(name="tests.inprocess.chord_body")
    def chord_body(results: list[int]) -> int:
        seen.append(list(results))
        return sum(results)

    try:
        workflow = chord(
            group(chord_header.s(1), chord_header.s(2), chord_header.s(3)),
            chord_body.s(),
        )
        assert worker.execute_work(workflow) == 12
        assert seen == [[2, 4, 6]]
    finally:
        worker.shutdown()


def test_inprocess_submit_canvas_async():
    cfg = get_settings(reload=True)
    worker = InProcessWorker(cfg)
    ran: list[str] = []

    @celery_app.task(name="tests.inprocess.canvas_async")
    def canvas_async(value: str) -> str:
        ran.append(value)
        return value

    try:
        result = worker.submit_canvas(canvas_async.si("async-ok"))
        assert result.id
        deadline = time.time() + 5
        while time.time() < deadline and not ran:
            time.sleep(0.05)
        assert ran == ["async-ok"]
    finally:
        worker.shutdown()


def test_inprocess_run_callable_reraises_failure():
    cfg = get_settings(reload=True)
    worker = InProcessWorker(cfg)

    @celery_app.task(name="tests.inprocess.boom")
    def boom() -> None:
        raise RuntimeError("task exploded")

    try:
        with pytest.raises(RuntimeError, match="task exploded"):
            worker._run_callable(boom, (), {})
    finally:
        worker.shutdown()


def test_resolve_task_rejects_non_task_object():
    cfg = get_settings(reload=True)
    worker = InProcessWorker(cfg)
    try:
        with pytest.raises(TypeError, match="Cannot resolve"):
            worker._resolve_task(object())
    finally:
        worker.shutdown()


def test_work_type_rejects_unknown_object():
    cfg = get_settings(reload=True)
    worker = InProcessWorker(cfg)
    try:
        with pytest.raises(ValueError, match="Cannot determine canvas type"):
            worker._work_type(object())
    finally:
        worker.shutdown()


def test_inprocess_beat_skips_unsupported_schedule(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(ipw_mod, "_BEAT_TICK_SECS", 0.05)
    monkeypatch.setattr(
        celery_app.conf,
        "beat_schedule",
        {"bad": {"task": "tests.inprocess.unused", "schedule": "cron-not-supported"}},
    )
    worker = InProcessWorker(cfg)
    try:
        time.sleep(0.15)
        assert worker._beat_thread is not None
    finally:
        worker.shutdown()


def test_submit_by_name_dispatches_registered_task():
    cfg = get_settings(reload=True)
    worker = InProcessWorker(cfg)
    ran: list[str] = []

    @celery_app.task(name="tests.inprocess.by_name")
    def by_name(value: str) -> str:
        ran.append(value)
        return value

    try:
        task_id = worker.submit_by_name("tests.inprocess.by_name", args=("named",))
        assert task_id
        deadline = time.time() + 5
        while time.time() < deadline and not ran:
            time.sleep(0.05)
        assert ran == ["named"]
    finally:
        worker.shutdown()

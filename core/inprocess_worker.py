"""
In-process task worker for desktop mode (ADR-001 §4.2).

Thread pool for CPU/IO (``default`` queue) and a bounded GPU executor for
``run_transcribe`` / ``process_clip``. Executes Celery canvas primitives
(chain, group, chord) without a broker.
"""

from __future__ import annotations

import importlib
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import timedelta
from typing import Any

import structlog

from core.celery_app import celery_app
from core.config import Settings, get_settings

log = structlog.get_logger(__name__)

GPU_TASKS = frozenset({
    "core.tasks.pipeline_tasks.run_transcribe",
    "core.tasks.pipeline_tasks.process_clip",
})

# Beat loop wake-up granularity; entries fire on their own intervals.
_BEAT_TICK_SECS = 1.0


def _import_task_modules() -> None:
    """
    Populate ``celery_app.tasks`` with every task module so by-name dispatch
    (vault copy, notify emails, training export) resolves without a broker.
    Runtime importlib call (not top-level imports) because the task modules
    themselves import this module via ``core.task_runner`` — a top-level
    import would be circular.
    """
    for module in celery_app.conf.include or ():
        importlib.import_module(module)

_worker: InProcessWorker | None = None
_worker_lock = threading.Lock()


class InProcessAsyncResult:
    """Minimal Celery AsyncResult stand-in (``.id`` only)."""

    def __init__(self, task_id: str) -> None:
        self.id = task_id


class InProcessWorker:
    def __init__(self, cfg: Settings) -> None:
        self._cfg = cfg
        self._default_pool = ThreadPoolExecutor(
            max_workers=cfg.queue.default_workers,
            thread_name_prefix="streamclip-default",
        )
        self._gpu_pool = ThreadPoolExecutor(
            max_workers=cfg.queue.gpu_workers,
            thread_name_prefix="streamclip-gpu",
        )
        self._orchestrator = ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="streamclip-orch",
        )
        self._beat_stop = threading.Event()
        self._beat_thread: threading.Thread | None = None
        if cfg.queue.inprocess_beat:
            self._beat_thread = threading.Thread(
                target=self._beat_loop,
                name="streamclip-beat",
                daemon=True,
            )
            self._beat_thread.start()

    def shutdown(self, *, wait: bool = True) -> None:
        self._beat_stop.set()
        if self._beat_thread is not None:
            self._beat_thread.join(timeout=_BEAT_TICK_SECS * 2)
            self._beat_thread = None
        self._orchestrator.shutdown(wait=wait, cancel_futures=False)
        self._default_pool.shutdown(wait=wait, cancel_futures=False)
        self._gpu_pool.shutdown(wait=wait, cancel_futures=False)

    def _beat_loop(self) -> None:
        """
        Minimal Celery Beat stand-in: run each ``beat_schedule`` entry on its
        interval so scheduled publishes (``process_due_scheduled_jobs``) and
        periodic cleanup fire in desktop mode. Entries fire only while the
        app is running; overdue work catches up on the next tick because the
        beat tasks themselves promote everything past due.
        """
        entries: list[dict[str, Any]] = []
        for entry_name, entry in (celery_app.conf.beat_schedule or {}).items():
            schedule = entry.get("schedule")
            if isinstance(schedule, timedelta):
                interval = schedule.total_seconds()
            elif isinstance(schedule, (int, float)):
                interval = float(schedule)
            else:
                log.warning("inprocess_beat_unsupported_schedule", entry=entry_name)
                continue
            entries.append({
                "name": entry_name,
                "task": entry["task"],
                "interval": interval,
                "next_run": time.monotonic() + interval,
            })
        if not entries:
            return
        log.info("inprocess_beat_started", entries=[e["name"] for e in entries])
        while not self._beat_stop.wait(timeout=_BEAT_TICK_SECS):
            now = time.monotonic()
            for entry in entries:
                if now < entry["next_run"]:
                    continue
                entry["next_run"] = now + entry["interval"]
                try:
                    self.submit_by_name(entry["task"])
                except Exception as exc:
                    log.error(
                        "inprocess_beat_dispatch_failed",
                        task=entry["task"],
                        error=str(exc),
                    )

    def _route_queue(self, task_name: str, explicit: str | None = None) -> str:
        if explicit:
            return explicit
        if task_name in GPU_TASKS:
            return "gpu"
        return "default"

    def _executor_for_queue(self, queue: str) -> ThreadPoolExecutor:
        return self._gpu_pool if queue == "gpu" else self._default_pool

    def _resolve_task(self, task: Any) -> Any:
        if hasattr(task, "run") and hasattr(task, "name"):
            return task
        if isinstance(task, str):
            registered = celery_app.tasks.get(task)
            if registered is None:
                raise KeyError(f"Unknown task name: {task}")
            return registered
        raise TypeError(f"Cannot resolve task: {task!r}")

    def _run_callable(self, task: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        celery_task = self._resolve_task(task)
        log.info("inprocess_task_start", name=celery_task.name, args=len(args))
        try:
            return celery_task.run(*args, **kwargs)
        except Exception as exc:
            log.error(
                "inprocess_task_failure",
                name=celery_task.name,
                error=str(exc),
                exc_type=type(exc).__name__,
            )
            # There is no broker here to run the task's failure path, so invoke
            # on_failure directly — otherwise the job would hang forever with no
            # error status (the desktop "stuck in processing" bug).
            on_failure = getattr(celery_task, "on_failure", None)
            if callable(on_failure):
                try:
                    on_failure(exc, str(uuid.uuid4()), args, kwargs, None)
                except Exception:
                    log.error("inprocess_on_failure_error", name=celery_task.name)
            raise
        finally:
            log.info("inprocess_task_end", name=celery_task.name)

    def _submit_callable(
        self,
        task: Any,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        *,
        queue: str | None = None,
    ) -> Future[Any]:
        celery_task = self._resolve_task(task)
        q = self._route_queue(celery_task.name, queue)
        pool = self._executor_for_queue(q)
        return pool.submit(self._run_callable, celery_task, args, kwargs)

    def submit_task(
        self,
        task: Any,
        *,
        args: tuple[Any, ...] | None = None,
        kwargs: dict[str, Any] | None = None,
        queue: str | None = None,
    ) -> str:
        task_id = str(uuid.uuid4())
        args = args or ()
        kwargs = kwargs or {}

        def _dispatch() -> None:
            self._submit_callable(task, args, kwargs, queue=queue).result()

        self._orchestrator.submit(_dispatch)
        return task_id

    def submit_by_name(
        self,
        name: str,
        *,
        args: tuple[Any, ...] | None = None,
        kwargs: dict[str, Any] | None = None,
        queue: str | None = None,
    ) -> str:
        return self.submit_task(name, args=args, kwargs=kwargs, queue=queue)

    def submit_canvas(self, work: Any, **opts: Any) -> InProcessAsyncResult:  # noqa: ARG002
        task_id = str(uuid.uuid4())
        self._orchestrator.submit(self._execute_canvas, work, task_id)
        return InProcessAsyncResult(task_id)

    def _execute_canvas(self, work: Any, task_id: str) -> Any:
        log.info("inprocess_canvas_start", task_id=task_id, work_type=self._work_type(work))
        try:
            return self.execute_work(work)
        except Exception as exc:
            log.error("inprocess_canvas_failure", task_id=task_id, error=str(exc))
            raise
        finally:
            log.info("inprocess_canvas_end", task_id=task_id)

    def _work_type(self, work: Any) -> str:
        st = getattr(work, "subtask_type", None)
        if st:
            return str(st)
        if hasattr(work, "task") or hasattr(work, "name"):
            return "task"
        raise ValueError(f"Cannot determine canvas type for {work!r}")

    def execute_work(self, work: Any) -> Any:
        subtask_type = self._work_type(work)

        if subtask_type == "chain":
            result: Any = None
            for sig in work.tasks:
                if getattr(sig, "immutable", False):
                    result = self.execute_work(sig)
                else:
                    result = self.execute_work(self._chain_link(sig, result))
            return result

        if subtask_type == "group":
            futures = [self._submit_signature(sig) for sig in work.tasks]
            return [f.result() for f in futures]

        if subtask_type == "chord":
            # Celery stores header signatures on ``.tasks`` and the callback on
            # ``.body`` (not ``tasks[1]``). Header may be a flat tuple of
            # signatures or a nested group — normalize to a group run.
            header = work.tasks
            callback = getattr(work, "body", None)
            if callback is None:
                raise ValueError("Chord missing body callback")
            if getattr(header, "subtask_type", None) == "group":
                group_results = self.execute_work(header)
            else:
                futures = [self._submit_signature(sig) for sig in header]
                group_results = [f.result() for f in futures]
            merged = self._chord_callback(callback, group_results)
            return self.execute_work(merged)

        if subtask_type == "task":
            return self._submit_signature(work).result()

        raise ValueError(f"Unsupported canvas type: {subtask_type!r}")

    @staticmethod
    def _chain_link(sig: Any, prev_result: Any) -> Any:
        args = tuple(sig.args or ())
        if prev_result is not None:
            args = (prev_result,) + args
        return sig.clone(args=args)

    @staticmethod
    def _chord_callback(sig: Any, group_results: list[Any]) -> Any:
        args = tuple(sig.args or ())
        return sig.clone(args=(group_results,) + args)

    def _submit_signature(self, sig: Any) -> Future[Any]:
        task_name = sig.name or sig.task
        if not task_name:
            raise ValueError("Signature missing task name")
        args = tuple(sig.args or ())
        kwargs = dict(sig.kwargs or {})
        options = dict(getattr(sig, "options", None) or {})
        queue = options.get("queue")
        return self._submit_callable(task_name, args, kwargs, queue=queue)


def get_worker() -> InProcessWorker | None:
    return _worker


def start_inprocess_worker(cfg: Settings | None = None) -> InProcessWorker:
    global _worker
    settings = cfg or get_settings()
    with _worker_lock:
        if _worker is not None:
            return _worker
        _import_task_modules()
        _worker = InProcessWorker(settings)
        log.info(
            "inprocess_worker_started",
            default_workers=settings.queue.default_workers,
            gpu_workers=settings.queue.gpu_workers,
            beat=settings.queue.inprocess_beat,
        )
        return _worker


def stop_inprocess_worker(*, wait: bool = True) -> None:
    global _worker
    with _worker_lock:
        if _worker is None:
            return
        _worker.shutdown(wait=wait)
        _worker = None
        log.info("inprocess_worker_stopped")

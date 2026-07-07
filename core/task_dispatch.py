"""
Task dispatch seam — Celery today, in-process worker for desktop .exe (ADR-001 §4.2).

API and services call `dispatch_task` instead of `.apply_async` / `.delay` directly
so the backend can switch without route changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from core.config import Settings, get_settings
from core.inprocess_worker import get_worker, start_inprocess_worker

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class TaskHandle:
    """Minimal async result handle (Celery AsyncResult or in-process stub)."""
    id: str


def dispatch_task(
    task: Any,
    *,
    args: tuple[Any, ...] | None = None,
    kwargs: dict[str, Any] | None = None,
    queue: str | None = None,
    cfg: Settings | None = None,
) -> TaskHandle:
    """
    Enqueue a Celery task, or run in-process when ``queue.backend=inprocess``.
    """
    settings = cfg or get_settings()
    args = args or ()
    kwargs = kwargs or {}

    if settings.queue.backend == "inprocess":
        worker = get_worker() or start_inprocess_worker(settings)
        task_id = worker.submit_task(task, args=args, kwargs=kwargs, queue=queue)
        return TaskHandle(id=task_id)

    opts: dict[str, Any] = {}
    if queue:
        opts["queue"] = queue
    result = task.apply_async(args=args, kwargs=kwargs, **opts)
    return TaskHandle(id=str(result.id))


def dispatch_task_by_name(
    name: str,
    *,
    args: tuple[Any, ...] | None = None,
    kwargs: dict[str, Any] | None = None,
    queue: str | None = None,
    cfg: Settings | None = None,
) -> TaskHandle:
    """Send by task name (avoids circular imports for notify tasks)."""
    settings = cfg or get_settings()
    args = args or ()
    kwargs = kwargs or {}

    if settings.queue.backend == "inprocess":
        worker = get_worker() or start_inprocess_worker(settings)
        task_id = worker.submit_by_name(name, args=args, kwargs=kwargs, queue=queue)
        return TaskHandle(id=task_id)

    from core.celery_app import celery_app

    opts: dict[str, Any] = {}
    if queue:
        opts["queue"] = queue
    result = celery_app.send_task(name, args=args, kwargs=kwargs, **opts)
    return TaskHandle(id=str(result.id))

"""
Task runner seam — routes Celery canvas / task dispatch to broker or in-process worker.

Pipeline tasks call ``apply_async`` / ``delay`` through this module so the same
code path works for Docker (Celery) and desktop (.exe) without edits at call sites.
"""

from __future__ import annotations

from typing import Any

from core.config import Settings, get_settings
from core.inprocess_worker import InProcessAsyncResult, get_worker, start_inprocess_worker


def _inprocess_enabled(cfg: Settings | None = None) -> bool:
    return (cfg or get_settings()).queue.backend == "inprocess"


def apply_async(work: Any, **opts: Any) -> Any:
    """Submit a Celery signature, chain, group, or chord."""
    cfg = get_settings()
    if not _inprocess_enabled(cfg):
        return work.apply_async(**opts)

    worker = get_worker() or start_inprocess_worker(cfg)
    return worker.submit_canvas(work, **opts)


def delay(task: Any, *args: Any, **kwargs: Any) -> Any:
    """Fire-and-forget single task (``.delay`` equivalent)."""
    cfg = get_settings()
    if not _inprocess_enabled(cfg):
        return task.delay(*args, **kwargs)

    worker = get_worker() or start_inprocess_worker(cfg)
    task_id = worker.submit_task(task, args=args, kwargs=kwargs)
    return InProcessAsyncResult(task_id)

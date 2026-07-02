"""Redis-backed pipeline stage clocks for elapsed time and ETA in SSE events."""

from __future__ import annotations

import json
import time
from typing import Any

import structlog

from core.config import get_settings
from core.eta import (
    canonical_stage,
    estimate_remaining_seconds,
)

log = structlog.get_logger(__name__)

TIMING_KEY_PREFIX = "streamclip:job:timing:"


def _timing_key(job_id: str) -> str:
    cfg = get_settings()
    return f"{TIMING_KEY_PREFIX}{job_id}"


def _load_state(r: Any, job_id: str) -> dict[str, Any]:
    raw = r.get(_timing_key(job_id))
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _save_state(r: Any, job_id: str, state: dict[str, Any]) -> None:
    cfg = get_settings()
    r.set(_timing_key(job_id), json.dumps(state), ex=cfg.redis.progress_ttl_secs)


def ensure_pipeline_started(r: Any, job_id: str) -> dict[str, Any]:
    """Initialize timing state at pipeline start (ingest)."""
    state = _load_state(r, job_id)
    now = time.time()
    if state.get("pipeline_started_at") is None:
        state = {
            "pipeline_started_at": now,
            "current_stage": "ingest",
            "current_stage_started_at": now,
            "stage_durations": {},
            "eta_context": state.get("eta_context"),
        }
        _save_state(r, job_id, state)
    return state


def set_eta_context(r: Any, job_id: str, eta_context: dict[str, Any]) -> None:
    state = _load_state(r, job_id)
    if not state.get("pipeline_started_at"):
        ensure_pipeline_started(r, job_id)
        state = _load_state(r, job_id)
    state["eta_context"] = eta_context
    _save_state(r, job_id, state)


def record_stage_progress(
    r: Any,
    job_id: str,
    *,
    stage: str,
    cfg: Any,
) -> dict[str, Any]:
    """
    Update stage clocks when progress is published.
    Returns timing fields to merge into the SSE payload.
    """
    state = ensure_pipeline_started(r, job_id)
    now = time.time()
    canonical = canonical_stage(stage)
    prev_stage = state.get("current_stage")
    stage_durations: dict[str, float] = dict(state.get("stage_durations") or {})

    if prev_stage and prev_stage != canonical:
        started = state.get("current_stage_started_at", now)
        elapsed = max(0.0, now - started)
        stage_durations[prev_stage] = stage_durations.get(prev_stage, 0.0) + elapsed
        state["current_stage"] = canonical
        state["current_stage_started_at"] = now
    elif prev_stage is None:
        state["current_stage"] = canonical
        state["current_stage_started_at"] = now

    state["stage_durations"] = stage_durations
    _save_state(r, job_id, state)

    pipeline_started = state.get("pipeline_started_at", now)
    stage_started = state.get("current_stage_started_at", now)
    total_elapsed = max(0.0, now - pipeline_started)
    stage_elapsed = max(0.0, now - stage_started)

    eta_context = state.get("eta_context") or {}
    eta_secs: float | None = None
    if eta_context.get("duration_secs"):
        eta_secs = estimate_remaining_seconds(
            canonical,
            stage_durations=stage_durations,
            stage_elapsed_secs=stage_elapsed,
            duration_secs=float(eta_context["duration_secs"]),
            source_kind=str(eta_context.get("source_kind", "url")),
            target_clips=int(eta_context.get("target_clips", 5)),
            skip_optical_flow=bool(eta_context.get("skip_optical_flow", False)),
            cfg=cfg,
            file_size_bytes=eta_context.get("file_size_bytes"),
        )

    return {
        "stage_elapsed_secs": round(stage_elapsed, 1),
        "total_elapsed_secs": round(total_elapsed, 1),
        "eta_secs": round(eta_secs, 1) if eta_secs is not None else None,
        "stage_durations": {k: round(v, 1) for k, v in stage_durations.items()},
    }


def finalize_timing(r: Any, job_id: str) -> dict[str, float]:
    """Close the current stage and return final stage_durations for DB persistence."""
    state = _load_state(r, job_id)
    if not state:
        return {}
    now = time.time()
    stage_durations: dict[str, float] = dict(state.get("stage_durations") or {})
    current = state.get("current_stage")
    if current:
        started = state.get("current_stage_started_at", now)
        stage_durations[current] = stage_durations.get(current, 0.0) + max(0.0, now - started)
    state["stage_durations"] = stage_durations
    _save_state(r, job_id, state)
    return {k: round(v, 1) for k, v in stage_durations.items()}

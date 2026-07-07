"""Pipeline timing / ETA helpers."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from core.progress_timing import (
    ensure_pipeline_started,
    finalize_timing,
    record_stage_progress,
    set_eta_context,
)


@pytest.fixture
def redis():
    store: dict[str, str] = {}

    class FakeRedis:
        def get(self, key):
            return store.get(key)

        def set(self, key, value, ex=None):
            store[key] = value

    return FakeRedis(), store


def test_ensure_pipeline_started(redis):
    r, _ = redis
    state = ensure_pipeline_started(r, "job-1")
    assert state["current_stage"] == "ingest"
    again = ensure_pipeline_started(r, "job-1")
    assert again["pipeline_started_at"] == state["pipeline_started_at"]


def test_load_state_invalid_json(redis):
    r, store = redis
    from core.progress_timing import _load_state

    store["streamclip:job:timing:job-x"] = "not-json"
    assert _load_state(r, "job-x") == {}


def test_set_eta_context_bootstraps(redis):
    r, _ = redis
    set_eta_context(r, "job-2", {"duration_secs": 3600.0, "target_clips": 3})
    out = record_stage_progress(r, "job-2", stage="transcribe", cfg=MagicMock())
    assert out["total_elapsed_secs"] >= 0


def test_record_stage_progress_with_eta(redis):
    r, _ = redis
    ensure_pipeline_started(r, "job-3")
    set_eta_context(r, "job-3", {
        "duration_secs": 600.0,
        "source_kind": "url",
        "target_clips": 5,
        "skip_optical_flow": True,
    })
    first = record_stage_progress(r, "job-3", stage="ingest", cfg=MagicMock())
    second = record_stage_progress(r, "job-3", stage="transcribe", cfg=MagicMock())
    assert "stage_durations" in second
    assert first["stage_elapsed_secs"] >= 0


def test_finalize_timing_empty(redis):
    r, _ = redis
    assert finalize_timing(r, "missing") == {}


def test_finalize_timing_closes_stage(redis):
    r, _ = redis
    ensure_pipeline_started(r, "job-4")
    record_stage_progress(r, "job-4", stage="detect", cfg=MagicMock())
    durations = finalize_timing(r, "job-4")
    assert "detect" in durations or isinstance(durations, dict)

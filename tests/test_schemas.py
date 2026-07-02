"""Pydantic schema tests."""

from __future__ import annotations

import pytest

from backend.api.schemas import CreateJobRequest, HealthResponse, ProgressEvent, UpdateClipRequest


def test_create_job_defaults():
    req = CreateJobRequest(source_url="https://example.com/v.mp4")
    assert req.target_clips == 5
    assert req.caption_style == "gaming_impact"


def test_health_response_shape():
    h = HealthResponse(version="1.0.0", environment="test", redis=True, database=True, storage=True)
    assert h.status == "ok"


def test_progress_event_timing_fields():
    e = ProgressEvent(
        job_id="abc",
        stage="transcribing",
        progress=0.2,
        ts=1.0,
        stage_elapsed_secs=12.5,
        total_elapsed_secs=120.0,
        eta_secs=300.0,
        stage_durations={"ingest": 45.0},
    )
    assert e.eta_secs == 300.0
    assert e.stage_durations["ingest"] == 45.0


def test_update_clip_request_title_hook():
    req = UpdateClipRequest(
        title="New title",
        hook="Watch this play",
        start_secs=10.0,
        end_secs=25.0,
        caption_style="tiktok_pop",
        reframe_preset="moba",
        overlay_enabled=False,
        rerender=True,
    )
    assert req.title == "New title"
    assert req.hook == "Watch this play"
    assert req.rerender is True


def test_update_clip_request_partial():
    req = UpdateClipRequest(start_secs=5.0, end_secs=15.0)
    assert req.title is None
    assert req.rerender is True

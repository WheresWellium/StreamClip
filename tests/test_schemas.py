"""Pydantic schema tests."""

from __future__ import annotations

from backend.api.schemas import CreateJobRequest, HealthResponse, ProgressEvent


def test_create_job_defaults():
    req = CreateJobRequest(source_url="https://example.com/v.mp4")
    assert req.target_clips == 5
    assert req.caption_style == "gaming_impact"


def test_health_response_shape():
    h = HealthResponse(version="1.0.0", environment="test", redis=True, database=True, storage=True)
    assert h.status == "ok"


def test_progress_event():
    e = ProgressEvent(job_id="abc", stage="ingesting", progress=0.1, ts=1.0)
    assert e.message == ""
    assert e.status == "processing"

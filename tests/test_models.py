"""Repository and model unit tests."""

from __future__ import annotations

from backend.db.models import ClipStatus, JobStatus, UserTier, _enum_values


def test_enum_values_match_postgres():
    assert _enum_values(JobStatus) == [
        "queued", "ingesting", "transcribing", "detecting",
        "processing", "done", "error", "cancelled",
    ]
    assert _enum_values(ClipStatus) == ["pending", "processing", "done", "error"]
    assert _enum_values(UserTier) == ["free", "pro", "admin"]

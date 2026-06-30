"""Storage helper tests."""

from __future__ import annotations

from core.storage import upload_key


def test_upload_key_anonymous():
    key = upload_key(None, "abc123", "video.mp4")
    assert key == "uploads/anonymous/abc123/video.mp4"

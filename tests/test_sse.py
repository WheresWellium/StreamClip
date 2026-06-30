"""SSE relay contract tests."""

from __future__ import annotations

import json

import pytest

from backend.services.sse import _format_sse


def test_format_sse_event():
    payload = json.dumps({"stage": "ingesting", "progress": 0.1})
    frame = _format_sse(payload, event="progress")
    assert "event: progress" in frame
    assert json.loads(frame.split("data: ", 1)[1].strip())["stage"] == "ingesting"

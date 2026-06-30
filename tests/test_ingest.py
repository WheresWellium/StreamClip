"""Ingest failure mode tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.config import get_settings
from core.errors import IngestError, StreamClipError
from core.ingest import IngestRequest, IngestService


def test_missing_local_file_raises(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    cfg.workspace_dir = tmp_path
    missing = tmp_path / "nope.mp4"
    service = IngestService(cfg)
    request = IngestRequest(job_id="test-job", local_path=missing)
    with pytest.raises((IngestError, FileNotFoundError, RuntimeError, StreamClipError)):
        service.run(request)

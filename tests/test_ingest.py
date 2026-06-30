"""Ingest failure mode tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.errors import IngestError
from core.ingest import ingest
from core.config import get_settings


def test_missing_local_file_raises(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    cfg.workspace_dir = tmp_path
    missing = tmp_path / "nope.mp4"
    with pytest.raises((IngestError, FileNotFoundError, RuntimeError)):
        ingest(missing, cfg)

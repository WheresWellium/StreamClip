"""IngestService orchestration tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.config import Settings
from core.ingest.service import IngestService
from core.ingest.types import IngestRequest, ProcessingTier, SourceKind
from core.models import VideoMeta


@pytest.fixture
def cfg(tmp_path):
    workspace = tmp_path / "workspace"
    cache = tmp_path / "cache"
    workspace.mkdir(parents=True)
    cache.mkdir(parents=True)
    return Settings(workspace_dir=workspace, cache_dir=cache)


def test_upload_ingest_keeps_storage_key_and_short_tier_hints(cfg, tmp_path, monkeypatch):
    source = tmp_path / "upload.mp4"
    source.write_bytes(b"\x00" * 64)

    mock_storage = MagicMock()
    mock_storage.exists.return_value = True

    meta = VideoMeta(
        path=source,
        title="upload",
        duration=30.0,
        width=1280,
        height=720,
        fps=30.0,
        url=None,
        size_bytes=64,
        has_audio=True,
        video_codec="h264",
        audio_codec="aac",
    )

    monkeypatch.setattr(
        "core.ingest.service.download_from_storage",
        lambda key, dest, _cfg, _store: meta,
    )

    svc = IngestService(cfg, storage=mock_storage)
    result = svc.run(
        IngestRequest(job_id="job-1", storage_key="uploads/user/clip.mp4"),
    )

    assert result.source_kind == SourceKind.UPLOAD
    assert result.processing_tier == ProcessingTier.SHORT
    assert result.storage_key == "uploads/user/clip.mp4"
    assert result.pipeline_hints["skip_optical_flow"] is True
    snap = result.to_snapshot()
    assert snap["processing_tier"] == "short"
    assert snap["skip_optical_flow"] is True


def test_local_ingest_uploads_to_job_prefix(cfg, tmp_path, monkeypatch):
    source = tmp_path / "local.mp4"
    source.write_bytes(b"\x00" * 64)

    mock_storage = MagicMock()
    mock_storage.exists.return_value = False

    meta = VideoMeta(
        path=source,
        title="local",
        duration=400.0,
        width=1920,
        height=1080,
        fps=60.0,
        url=None,
        size_bytes=64,
        has_audio=True,
        video_codec="h264",
        audio_codec="aac",
    )

    monkeypatch.setattr(
        "core.ingest.service.resolve_local",
        lambda src, dest, _cfg: VideoMeta(**{**vars(meta), "path": dest}),
    )

    svc = IngestService(cfg, storage=mock_storage)
    result = svc.run(
        IngestRequest(job_id="job-2", local_path=source),
    )

    assert result.processing_tier == ProcessingTier.MEDIUM
    mock_storage.upload.assert_called_once()
    assert result.pipeline_hints["skip_optical_flow"] is False

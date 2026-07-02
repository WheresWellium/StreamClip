"""Deferred upload and ingest progress callback tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.config import Settings
from core.ingest.service import IngestService
from core.ingest.types import IngestRequest
from core.models import VideoMeta


@pytest.fixture
def cfg(tmp_path):
    workspace = tmp_path / "workspace"
    cache = tmp_path / "cache"
    workspace.mkdir(parents=True)
    cache.mkdir(parents=True)
    return Settings(
        workspace_dir=workspace,
        cache_dir=cache,
        ingest={"defer_source_upload": True},
    )


def test_url_ingest_skips_blocking_upload_when_deferred(cfg, tmp_path, monkeypatch):
    source = tmp_path / "cached.mp4"
    source.write_bytes(b"\x00" * 128)
    dest = cfg.workspace_dir / "jobs" / "job-defer" / "source.mp4"

    meta = VideoMeta(
        path=source,
        title="vod",
        duration=600.0,
        width=1920,
        height=1080,
        fps=30.0,
        url="https://example.com/v.mp4",
        size_bytes=128,
        has_audio=True,
        video_codec="h264",
        audio_codec="aac",
    )

    mock_storage = MagicMock()
    mock_storage.exists.return_value = False

    monkeypatch.setattr(
        "core.ingest.service.download_url",
        lambda *a, **k: (meta, False),
    )
    def _materialize(_self, _src, dest_path: Path) -> None:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(b"x")

    monkeypatch.setattr(
        "core.ingest.service.IngestService._materialize_to_workspace",
        _materialize,
    )

    svc = IngestService(cfg, storage=mock_storage)
    result = svc.run(IngestRequest(job_id="job-defer", source_url="https://example.com/v.mp4"))

    mock_storage.upload.assert_not_called()
    assert result.local_path.exists() or dest.exists()
    assert result.storage_key is not None


def test_storage_download_progress_callback(cfg, tmp_path):
    from core.ingest.resolvers.storage import download_from_storage

    dest = tmp_path / "out.mp4"
    progress_calls: list[float] = []

    mock_storage = MagicMock()
    mock_storage.size.return_value = 1000

    def fake_download(key, path, on_progress=None):
        if on_progress:
            on_progress(500, 1000)
            on_progress(1000, 1000)

    mock_storage.download.side_effect = fake_download

    meta = VideoMeta(
        path=dest,
        title="upload",
        duration=30.0,
        width=1280,
        height=720,
        fps=30.0,
        url=None,
        size_bytes=1000,
        has_audio=True,
        video_codec="h264",
        audio_codec="aac",
    )

    with patch("core.ingest.resolvers.storage.probe_video", return_value=meta):
        download_from_storage(
            "uploads/key.mp4",
            dest,
            cfg,
            storage=mock_storage,
            on_progress=lambda pct: progress_calls.append(pct),
        )

    assert progress_calls[-1] == 1.0
    assert any(0 < p < 1 for p in progress_calls)

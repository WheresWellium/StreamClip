"""Additional IngestService paths for coverage."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.config import get_settings
from core.errors import IngestError
from core.ingest.service import IngestService
from core.ingest.types import IngestRequest, ProcessingTier, SourceKind
from core.models import VideoMeta


def _meta(path: Path, **kw) -> VideoMeta:
    base = dict(
        path=path, url=None, title="t", duration=30.0,
        width=1920, height=1080, fps=30.0, size_bytes=1000,
        has_audio=True, video_codec="h264", audio_codec="aac",
    )
    base.update(kw)
    return VideoMeta(**base)


def _fake_audio_download(audio_meta: VideoMeta):
    def _download(_key, local_path, _cfg, _storage, on_progress=None):
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(b"fake-audio")
        return audio_meta
    return _download


def test_ingest_upload_audio_disabled_raises(tmp_path: Path):
    cfg = get_settings()
    cfg.workspace_dir = tmp_path
    cfg.features.audio_ingest = False
    storage = MagicMock()
    storage.size.return_value = 500
    audio_meta = _meta(tmp_path / "x", width=0, height=0, video_codec="none")

    with patch(
        "core.ingest.service.download_from_storage",
        side_effect=_fake_audio_download(audio_meta),
    ):
        svc = IngestService(cfg, storage)
        with pytest.raises(IngestError, match="Audio ingest disabled"):
            svc.run(
                IngestRequest(
                    job_id="j-audio-off",
                    storage_key="uploads/pod.mp3",
                ),
            )


def test_ingest_upload_audio_slate_and_hints(tmp_path: Path):
    cfg = get_settings()
    cfg.workspace_dir = tmp_path
    cfg.features.audio_ingest = True
    storage = MagicMock()
    storage.size.return_value = 500
    storage.upload.return_value = None
    audio_meta = _meta(tmp_path / "x", width=0, height=0, video_codec="none")
    slate_meta = _meta(tmp_path / "jobs/j-audio/source.mp4")

    messages: list[str] = []

    with patch(
        "core.ingest.service.download_from_storage",
        side_effect=_fake_audio_download(audio_meta),
    ), \
         patch("core.ingest.service.render_audio_slate"), \
         patch("core.ingest.service.probe_video", return_value=slate_meta), \
         patch("core.ingest.service.resolve_tier", return_value=ProcessingTier.SHORT):
        svc = IngestService(cfg, storage)
        result = svc.run(
            IngestRequest(
                job_id="j-audio",
                storage_key="uploads/pod.mp3",
            ),
            on_message=messages.append,
        )

    assert result.pipeline_hints["audio_source"] is True
    assert result.pipeline_hints["skip_optical_flow"] is True
    assert storage.upload.called
    assert any("slate" in m.lower() for m in messages)


def test_ingest_url_cache_hit_message(tmp_path: Path):
    cfg = get_settings()
    cfg.workspace_dir = tmp_path
    cfg.ingest.defer_source_upload = True
    storage = MagicMock()
    cached_path = tmp_path / "cache.mp4"
    cached_path.write_bytes(b"fake-video")
    cached = _meta(cached_path)
    messages: list[str] = []

    with patch("core.ingest.service.normalize_source_url", return_value="https://example.com/v"), \
         patch("core.ingest.service.resolve_tier", return_value=ProcessingTier.MEDIUM), \
         patch("core.ingest.service.download_url", return_value=(cached, True)), \
         patch("core.ingest.service.probe_video", return_value=cached):
        svc = IngestService(cfg, storage)
        result = svc.run(
            IngestRequest(
                job_id="j-url",
                source_url="https://example.com/v",
            ),
            on_message=messages.append,
        )

    assert result.source_kind == SourceKind.URL
    assert any("cached" in m.lower() for m in messages)


def test_ingest_local_uploads_when_not_deferred(tmp_path: Path):
    cfg = get_settings()
    cfg.workspace_dir = tmp_path
    cfg.ingest.defer_source_upload = False
    local_src = tmp_path / "in.mp4"
    local_src.write_bytes(b"fake")
    storage = MagicMock()
    storage.exists.return_value = False
    meta = _meta(local_src)

    with patch("core.ingest.service.resolve_local", return_value=meta), \
         patch("core.ingest.service.resolve_tier", return_value=ProcessingTier.LONG):
        svc = IngestService(cfg, storage)
        result = svc.run(
            IngestRequest(
                job_id="j-local",
                local_path=local_src,
            ),
        )

    storage.upload.assert_called_once()
    assert result.storage_key.endswith("source.mp4")


def test_ingest_upload_sets_file_size_from_local_stat(tmp_path: Path):
    cfg = get_settings()
    cfg.workspace_dir = tmp_path
    cfg.features.audio_ingest = True
    storage = MagicMock()
    storage.size.side_effect = RuntimeError("size unavailable")
    video_meta = _meta(tmp_path / "x")

    def fake_download(_key, local_path, _cfg, _storage, on_progress=None):
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(b"x" * 512)
        return video_meta

    with patch(
        "core.ingest.service.download_from_storage",
        side_effect=fake_download,
    ), patch("core.ingest.service.resolve_tier", return_value=ProcessingTier.MEDIUM):
        svc = IngestService(cfg, storage)
        result = svc.run(IngestRequest(job_id="j-stat", storage_key="uploads/v.mp4"))

    assert result.file_size_bytes == 512


def test_ingest_url_uploads_archive_when_not_deferred(tmp_path: Path):
    cfg = get_settings()
    cfg.workspace_dir = tmp_path
    cfg.ingest.defer_source_upload = False
    storage = MagicMock()
    storage.exists.return_value = False
    cached_path = tmp_path / "cache.mp4"
    cached_path.write_bytes(b"video")
    cached = _meta(cached_path)

    with patch("core.ingest.service.normalize_source_url", return_value="https://example.com/v"), \
         patch("core.ingest.service.resolve_tier", return_value=ProcessingTier.LONG), \
         patch("core.ingest.service.download_url", return_value=(cached, False)):
        svc = IngestService(cfg, storage)
        svc.run(IngestRequest(job_id="j-arch", source_url="https://example.com/v"))

    storage.upload.assert_called_once()


def test_materialize_to_workspace_skips_existing_dest(tmp_path: Path):
    src = tmp_path / "src.mp4"
    dest = tmp_path / "dest.mp4"
    src.write_bytes(b"new")
    dest.write_bytes(b"old")
    IngestService._materialize_to_workspace(src, dest)
    assert dest.read_bytes() == b"old"


def test_materialize_to_workspace_hardlinks_or_copies(tmp_path: Path):
    src = tmp_path / "src.mp4"
    dest = tmp_path / "dest.mp4"
    src.write_bytes(b"video")
    IngestService._materialize_to_workspace(src, dest)
    assert dest.read_bytes() == b"video"


def test_pipeline_hints_medium_tier_respects_config():
    cfg = get_settings()
    cfg.ingest.medium_skip_optical_flow = True
    svc = IngestService(cfg, MagicMock())
    hints = svc._pipeline_hints(ProcessingTier.MEDIUM)
    assert hints["skip_optical_flow"] is True

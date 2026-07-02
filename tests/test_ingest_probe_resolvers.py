"""probe_video and ingest resolvers."""
from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from core.config import get_settings
from core.errors import IngestError, StorageError
from core.ingest.probe import probe_video
from core.models import VideoMeta
from core.ingest.resolvers.local import resolve_local, _file_hash
from core.models import VideoMeta
from core.ingest.resolvers.storage import download_from_storage

FFPROBE_JSON = {
    "format": {"duration": "12.5", "size": "1000", "tags": {"title": "MyVid"}},
    "streams": [
        {"codec_type": "video", "width": 1920, "height": 1080, "r_frame_rate": "30/1", "codec_name": "h264"},
        {"codec_type": "audio", "codec_name": "aac"},
    ],
}

def test_probe_video_parses_ffprobe(tmp_path):
    p = tmp_path / "v.mp4"
    p.write_bytes(b"x")
    with patch("core.ingest.probe.subprocess.run") as run:
        run.return_value = MagicMock(stdout=json.dumps(FFPROBE_JSON), returncode=0)
        meta = probe_video(p, url="http://x")
    assert meta.width == 1920
    assert meta.has_audio
    assert meta.fps == 30.0

def test_probe_video_bad_fps(tmp_path):
    data = dict(FFPROBE_JSON)
    data["streams"] = [{"codec_type": "video", "width": 1, "height": 1, "r_frame_rate": "bad", "codec_name": "h264"}]
    p = tmp_path / "v.mp4"
    with patch("core.ingest.probe.subprocess.run") as run:
        run.return_value = MagicMock(stdout=json.dumps(data), returncode=0)
        meta = probe_video(p)
    assert meta.fps == 30.0

def test_file_hash_and_resolve_local(tmp_path):
    src = tmp_path / "src.mp4"
    src.write_bytes(b"hello world")
    dst = tmp_path / "ws" / "source.mp4"
    with patch("core.ingest.resolvers.local.probe_video") as probe:
        probe.return_value = VideoMeta(path=dst, url=None, title="t", duration=1.0, width=1, height=1, fps=30.0, size_bytes=1, has_audio=True, video_codec="h264", audio_codec="aac")
        meta = resolve_local(src, dst, get_settings())
    assert meta.path == dst
    assert _file_hash(src)

def test_resolve_local_missing():
    with pytest.raises(FileNotFoundError):
        resolve_local(Path("/no/such/file.mp4"), Path("/tmp/x.mp4"), get_settings())

def test_download_from_storage_reports_progress(tmp_path):
    dest = tmp_path / "dl.mp4"
    store = MagicMock()
    store.size.return_value = 200
    progress: list[float] = []

    def _download(key, local_dest, on_progress=None):
        if on_progress:
            on_progress(100, 200)
            on_progress(200, 200)

    store.download.side_effect = _download
    with patch("core.ingest.resolvers.storage.probe_video") as probe:
        probe.return_value = VideoMeta(
            path=dest, url=None, title="t", duration=2.0, width=1, height=1,
            fps=30.0, size_bytes=1, has_audio=False, video_codec="h264", audio_codec="none",
        )
        download_from_storage(
            "key", dest, get_settings(), storage=store,
            on_progress=progress.append,
        )
    assert progress == [0.5, 1.0]


def test_download_from_storage(tmp_path):
    dest = tmp_path / "dl.mp4"
    store = MagicMock()
    with patch("core.ingest.resolvers.storage.probe_video") as probe:
        probe.return_value = VideoMeta(path=dest, url=None, title="t", duration=2.0, width=1, height=1, fps=30.0, size_bytes=1, has_audio=False, video_codec="h264", audio_codec="none")
        meta = download_from_storage("key", dest, get_settings(), storage=store)
    store.download.assert_called_once()
    assert meta.path == dest

def test_download_storage_error(tmp_path):
    dest = tmp_path / "dl.mp4"
    store = MagicMock()
    store.download.side_effect = StorageError("missing")
    with pytest.raises(IngestError):
        download_from_storage("key", dest, get_settings(), storage=store)
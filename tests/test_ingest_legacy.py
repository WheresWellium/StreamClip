"""core/ingest.py legacy module (shadowed by package)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.config import get_settings
from core.models import VideoMeta


def _legacy():
    path = Path(__file__).resolve().parents[1] / "core" / "ingest.py"
    spec = importlib.util.spec_from_file_location("core_ingest_legacy", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_download_delegates():
    legacy = _legacy()
    cfg = get_settings()
    meta = VideoMeta(
        path=Path("/x.mp4"), url="u", title="t", duration=1.0,
        width=1, height=1, fps=30.0, size_bytes=1, has_audio=True,
        video_codec="h264", audio_codec="aac",
    )
    with patch.object(legacy, "download_url", return_value=(meta, False)) as du:
        out = legacy.download("https://example.com/v", cfg)
    assert out is meta
    du.assert_called_once()


def test_ingest_local_and_url(tmp_path):
    legacy = _legacy()
    cfg = get_settings(reload=True)
    meta = VideoMeta(
        path=tmp_path / "v.mp4", url=None, title="t", duration=1.0,
        width=1, height=1, fps=30.0, size_bytes=1, has_audio=False,
        video_codec="h264", audio_codec="",
    )
    result = MagicMock(meta=meta)
    with patch.object(legacy, "IngestService") as Svc:
        Svc.return_value.run.return_value = result
        assert legacy.ingest("https://youtube.com/x", cfg).title == "t"
        assert legacy.ingest(tmp_path / "f.mp4", cfg).title == "t"
        legacy.ingest_local(tmp_path / "f.mp4", cfg)

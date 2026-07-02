"""URL resolver tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from core.config import get_settings
from core.errors import IngestError
from core.ingest.resolvers.url import (
    _build_ytdlp_cmd,
    _max_height,
    _url_hash,
    download_url,
    fetch_subtitles_for_url,
)
from core.ingest.types import ProcessingTier
from core.models import VideoMeta


def test_url_hash_and_max_height():
    assert len(_url_hash("http://a")) == 16
    cfg = get_settings().ingest
    assert _max_height(ProcessingTier.SHORT, cfg) == cfg.short_max_height
    assert _max_height(ProcessingTier.MEDIUM, cfg) == cfg.medium_max_height
    assert _max_height(ProcessingTier.LONG, cfg) == cfg.long_max_height


def test_build_ytdlp_cmd_video_has_concurrent_fragments():
    cmd = _build_ytdlp_cmd(
        "u", Path("o.mp4"), max_height=720, concurrent_fragments=4,
    )
    assert "--concurrent-fragments" in cmd
    assert "4" in cmd
    assert "--write-auto-subs" not in cmd


def test_build_ytdlp_cmd_subs_only():
    cmd = _build_ytdlp_cmd(
        "u", Path("o.mp4"), max_height=720, concurrent_fragments=4, subs_only=True,
    )
    assert "--write-auto-subs" in cmd
    assert "--skip-download" in cmd
    assert "--concurrent-fragments" not in cmd


def test_download_cache_hit(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "cache_dir", tmp_path)
    url = "https://example.com/v"
    h = _url_hash(url)
    vid = tmp_path / f"{h}.mp4"
    vid.write_bytes(b"x")
    (tmp_path / f"{h}.json").write_text(json.dumps({"title": "T"}))
    meta = VideoMeta(
        path=vid,
        duration=1.0,
        width=1,
        height=1,
        fps=30.0,
        video_codec="h264", audio_codec="aac", size_bytes=1, has_audio=True,
        title="orig",
        url=url,
    )
    with patch("core.ingest.resolvers.url.probe_video", return_value=meta):
        out, was_cache_hit = download_url(url, cfg, tier=ProcessingTier.SHORT)
    assert out.title == "T"
    assert was_cache_hit is True


def test_download_ytdlp_success(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "cache_dir", tmp_path)
    url = "https://example.com/v2"
    h = _url_hash(url)
    tmp = tmp_path / f"{h}.tmp.mp4"

    class Proc:
        returncode = 0
        stdout = iter(["[download] 50.0%"])

        def wait(self):
            tmp.write_bytes(b"data")

    meta = VideoMeta(
        path=tmp_path / f"{h}.mp4",
        duration=2.0,
        width=640,
        height=360,
        fps=30.0,
        video_codec="h264", audio_codec="aac", size_bytes=1, has_audio=True,
        title="t",
        url=url,
    )
    with patch("core.ingest.resolvers.url.subprocess.Popen", return_value=Proc()):
        with patch("core.ingest.resolvers.url.probe_video", return_value=meta):
            out, was_cache_hit = download_url(
                url, cfg, tier=ProcessingTier.MEDIUM, on_progress=lambda p: None,
            )
    assert out.duration == 2.0
    assert was_cache_hit is False


def test_download_ytdlp_fail():
    cfg = get_settings(reload=True)

    class Proc:
        returncode = 1
        stdout = iter([])

        def wait(self):
            pass

    with patch("core.ingest.resolvers.url.subprocess.Popen", return_value=Proc()):
        with pytest.raises(IngestError):
            download_url("https://x", cfg, tier=ProcessingTier.SHORT)


def test_fetch_subtitles_skipped_when_disabled(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "cache_dir", tmp_path)
    cfg.ingest.fetch_subs_on_long = False
    with patch("core.ingest.resolvers.url.subprocess.run") as run:
        fetch_subtitles_for_url("https://x", cfg, tier=ProcessingTier.LONG)
    run.assert_not_called()

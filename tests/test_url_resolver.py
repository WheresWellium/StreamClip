"""URL resolver tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from core.config import get_settings
from core.errors import IngestError, NoAudioStreamError
from core.ingest.resolvers.url import (
    _build_ytdlp_cmd,
    _format_selector,
    _is_hls_platform,
    _is_transient_ytdlp_output,
    _max_height,
    _url_hash,
    _user_message_from_ytdlp,
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


def test_is_hls_platform():
    assert _is_hls_platform("https://www.twitch.tv/videos/1")
    assert _is_hls_platform("https://kick.com/video/abc")
    assert not _is_hls_platform("https://example.com/v.mp4")


def test_format_selector_always_requires_audio():
    yt = _format_selector(1080, hls=False)
    tw = _format_selector(1080, hls=True)
    # Progressive (YouTube etc.): prefer formats that declare an audio codec.
    assert "acodec!=none" in yt
    assert "+bestaudio" in yt
    # HLS (Twitch/Kick): acodec is often "unknown" on progressive MP4s — do not
    # filter with acodec!=none (rejects every format). Still require +bestaudio
    # merge paths; silent files are caught later by probe / NoAudioStreamError.
    assert "acodec!=none" not in tw
    assert "+bestaudio" in tw
    # Progressive still prefers acodec!=none paths before the bare-best fallback.
    assert yt.count("acodec!=none") >= 2
    assert yt.endswith("/best") or yt.endswith("best")


def test_build_ytdlp_cmd_video_has_concurrent_fragments():
    cfg = get_settings()
    cmd = _build_ytdlp_cmd(
        "https://example.com/v.mp4", Path("o.mp4"), cfg,
        max_height=720, concurrent_fragments=4,
    )
    assert "--concurrent-fragments" in cmd
    assert "4" in cmd
    assert "--write-auto-subs" not in cmd
    assert "--ffmpeg-location" in cmd
    ff_idx = cmd.index("--ffmpeg-location") + 1
    assert cmd[ff_idx]  # resolved path or binary name


def test_build_ytdlp_cmd_twitch_uses_hls_format_and_referer():
    cfg = get_settings()
    cmd = _build_ytdlp_cmd(
        "https://www.twitch.tv/videos/1", Path("o.mp4"), cfg,
        max_height=1080, concurrent_fragments=4,
    )
    fmt_idx = cmd.index("--format") + 1
    assert "ext=mp4" not in cmd[fmt_idx]
    # Twitch clips report acodec=unknown — selector must not require acodec!=none only.
    assert "best[height<=1080]" in cmd[fmt_idx]
    assert "--referer" in cmd
    assert "twitch.tv" in cmd[cmd.index("--referer") + 1]


def test_build_ytdlp_cmd_twitch_client_id_when_configured():
    cfg = get_settings(reload=True)
    cfg.twitch_client_id = "test-client-id"
    cmd = _build_ytdlp_cmd(
        "https://www.twitch.tv/videos/1", Path("o.mp4"), cfg,
        max_height=720, concurrent_fragments=4,
    )
    assert "--extractor-args" in cmd
    assert "client_id=test-client-id" in " ".join(cmd)


def test_build_ytdlp_cmd_subs_only():
    cfg = get_settings()
    cmd = _build_ytdlp_cmd(
        "https://example.com/v", Path("o.mp4"), cfg,
        max_height=720, concurrent_fragments=4, subs_only=True,
    )
    assert "--write-auto-subs" in cmd
    assert "--skip-download" in cmd
    assert "--concurrent-fragments" not in cmd


def test_transient_ytdlp_error_detection():
    lines = ["ERROR: 'NoneType' object is not subscriptable"]
    assert _is_transient_ytdlp_output(lines)
    assert "temporary" in _user_message_from_ytdlp(lines, "https://www.twitch.tv/videos/1")


def test_user_message_ip_blocked():
    lines = ["ERROR: [TikTok] 123: Your IP address is blocked from accessing this post"]
    msg = _user_message_from_ytdlp(lines, "https://www.tiktok.com/@x/video/123")
    assert "IP block" in msg


def test_user_message_live_stream_unavailable():
    lines = [
        "ERROR: [twitch:stream] aresthebot: 202: live stream unavailable, "
        "use a permanent link instead."
    ]
    msg = _user_message_from_ytdlp(lines, "https://www.twitch.tv/videos/1")
    assert "downloadable VOD" in msg
    assert "permanent link" not in msg.lower() or "videos/" in msg


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


def test_download_rejects_fresh_video_without_audio(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "cache_dir", tmp_path)
    cfg.ingest.ytdlp_max_retries = 1
    url = "https://example.com/silent"
    h = _url_hash(url)
    tmp = tmp_path / f"{h}.tmp.mp4"

    class Proc:
        returncode = 0
        stdout = iter(["[download] 100.0%"])

        def wait(self):
            tmp.write_bytes(b"data")

    silent = VideoMeta(
        path=tmp_path / f"{h}.mp4",
        duration=2.0,
        width=640,
        height=360,
        fps=30.0,
        video_codec="h264",
        audio_codec="none",
        size_bytes=1,
        has_audio=False,
        title="silent",
        url=url,
    )
    with patch("core.ingest.resolvers.url.subprocess.Popen", return_value=Proc()):
        with patch("core.ingest.resolvers.url.probe_video", return_value=silent):
            with pytest.raises(NoAudioStreamError):
                download_url(url, cfg, tier=ProcessingTier.SHORT)
    assert not (tmp_path / f"{h}.mp4").exists()


def test_download_invalidates_silent_cache_and_redownloads(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "cache_dir", tmp_path)
    cfg.ingest.ytdlp_max_retries = 1
    url = "https://example.com/cached-silent"
    h = _url_hash(url)
    cached = tmp_path / f"{h}.mp4"
    cached.write_bytes(b"old-silent")
    (tmp_path / f"{h}.json").write_text(json.dumps({"title": "old"}))
    tmp = tmp_path / f"{h}.tmp.mp4"

    silent = VideoMeta(
        path=cached,
        duration=1.0,
        width=1,
        height=1,
        fps=30.0,
        video_codec="h264",
        audio_codec="none",
        size_bytes=1,
        has_audio=False,
        title="old",
        url=url,
    )
    good = VideoMeta(
        path=tmp_path / f"{h}.mp4",
        duration=2.0,
        width=640,
        height=360,
        fps=30.0,
        video_codec="h264",
        audio_codec="aac",
        size_bytes=1,
        has_audio=True,
        title="fixed",
        url=url,
    )
    probes = iter([silent, good])

    class Proc:
        returncode = 0
        stdout = iter(["[download] 100.0%"])

        def wait(self):
            tmp.write_bytes(b"with-audio")

    with patch("core.ingest.resolvers.url.probe_video", side_effect=lambda *_a, **_k: next(probes)):
        with patch("core.ingest.resolvers.url.subprocess.Popen", return_value=Proc()):
            out, was_cache_hit = download_url(url, cfg, tier=ProcessingTier.SHORT)
    assert was_cache_hit is False
    assert out.has_audio is True
    assert out.title == "fixed"


def test_download_ytdlp_success(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "cache_dir", tmp_path)
    cfg.ingest.ytdlp_max_retries = 1
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


def test_download_ytdlp_retries_transient_failure(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "cache_dir", tmp_path)
    cfg.ingest.ytdlp_max_retries = 2
    cfg.ingest.ytdlp_retry_base_delay_secs = 0.01
    url = "https://www.twitch.tv/videos/99"
    h = _url_hash(url)
    tmp = tmp_path / f"{h}.tmp.mp4"
    calls = {"n": 0}

    class Proc:
        def __init__(self):
            calls["n"] += 1
            self.returncode = 0 if calls["n"] >= 2 else 1
            self.stdout = iter(
                ["ERROR: 'NoneType' object is not subscriptable"]
                if self.returncode != 0
                else ["[download] 100.0%"],
            )

        def wait(self):
            if self.returncode == 0:
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
    with patch("core.ingest.resolvers.url.subprocess.Popen", side_effect=lambda *a, **k: Proc()):
        with patch("core.ingest.resolvers.url.probe_video", return_value=meta):
            out, was_cache_hit = download_url(url, cfg, tier=ProcessingTier.LONG)
    assert calls["n"] == 2
    assert was_cache_hit is False
    assert out.duration == 2.0


def test_download_ytdlp_fail():
    cfg = get_settings(reload=True)
    cfg.ingest.ytdlp_max_retries = 1

    class Proc:
        returncode = 1
        stdout = iter(["ERROR: video unavailable"])

        def wait(self):
            pass

    with patch("core.ingest.resolvers.url.subprocess.Popen", return_value=Proc()):
        with pytest.raises(IngestError) as exc_info:
            download_url("https://x", cfg, tier=ProcessingTier.SHORT)
    assert "no longer available" in exc_info.value.user_message


def test_fetch_subtitles_skipped_when_disabled(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg, "cache_dir", tmp_path)
    cfg.ingest.fetch_subs_on_long = False
    with patch("core.ingest.resolvers.url.subprocess.run") as run:
        fetch_subtitles_for_url("https://x", cfg, tier=ProcessingTier.LONG)
    run.assert_not_called()

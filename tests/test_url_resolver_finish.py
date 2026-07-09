"""Finish url resolver coverage gaps (kick referer, ytdlp messages, retry unlink)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.config import get_settings
from core.errors import IngestError
from core.ingest.resolvers.url import (
    _build_ytdlp_cmd,
    _referer_for_url,
    _user_message_from_ytdlp,
    download_url,
)
from core.ingest.types import ProcessingTier

_TIER = ProcessingTier.SHORT


def test_referer_for_kick_url():
    args = _referer_for_url("https://kick.com/somechannel/video/123")
    assert args == ["--referer", "https://kick.com/"]


def test_user_message_subscriber_only():
    lines = ["ERROR: subscriber-only VOD"]
    msg = _user_message_from_ytdlp(lines, "https://www.twitch.tv/videos/1")
    assert "subscription" in msg.lower()


def test_user_message_private_login():
    lines = ["ERROR: login required — private video"]
    msg = _user_message_from_ytdlp(lines, "https://www.youtube.com/watch?v=abc")
    assert "private" in msg.lower() or "login" in msg.lower()


def test_download_ytdlp_retry_unlinks_partial(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    cfg.cache_dir = tmp_path
    cfg.ingest.ytdlp_max_retries = 2
    cfg.ingest.ytdlp_retry_base_delay_secs = 0.0
    url = "https://example.com/video.mp4"
    tmp_partial = tmp_path / "deadbeef.tmp.mp4"
    tmp_partial.write_bytes(b"partial")

    calls = {"n": 0}

    def fake_run(cmd, on_progress):
        calls["n"] += 1
        if calls["n"] == 1:
            return 1, ["HTTP Error 503: temporary failure"]
        tmp_partial.write_bytes(b"done")
        return 0, ["[download] 100%"]

    with patch("core.ingest.resolvers.url._url_hash", return_value="deadbeef"), \
         patch("core.ingest.resolvers.url._run_ytdlp", side_effect=fake_run), \
         patch("core.ingest.resolvers.url.probe_video") as probe, \
         patch("core.ingest.resolvers.url.time.sleep"):
        probe.return_value = MagicMock(
            title="T", duration=10.0, width=1920, height=1080,
            fps=30.0, size_bytes=100, has_audio=True,
            video_codec="h264", audio_codec="aac",
        )
        meta, cached = download_url(url, cfg, tier=_TIER)
    assert cached is False
    assert meta.title == "T"
    assert calls["n"] == 2
    assert not tmp_partial.exists()


def test_build_ytdlp_cmd_includes_kick_referer():
    cfg = get_settings()
    cmd = _build_ytdlp_cmd(
        "https://kick.com/video/abc",
        Path("/tmp/out.mp4"),
        cfg,
        max_height=720,
        concurrent_fragments=4,
    )
    assert "--referer" in cmd
    assert "kick.com" in cmd[cmd.index("--referer") + 1]


def test_download_ytdlp_non_transient_raises(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    cfg.cache_dir = tmp_path
    cfg.ingest.ytdlp_max_retries = 1
    url = "https://example.com/gone.mp4"

    with patch("core.ingest.resolvers.url._url_hash", return_value="gone1234"), \
         patch("core.ingest.resolvers.url._run_ytdlp", return_value=(1, ["video unavailable"])):
        with pytest.raises(IngestError) as exc:
            download_url(url, cfg, tier=_TIER)
    assert "no longer available" in exc.value.user_message.lower()

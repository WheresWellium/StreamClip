"""Unit tests for core.ytdlp_bin — no network."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from core import ytdlp_bin


@pytest.fixture(autouse=True)
def _clear_cache():
    ytdlp_bin.ytdlp_argv.cache_clear()
    yield
    ytdlp_bin.ytdlp_argv.cache_clear()


def test_ytdlp_argv_prefers_env(tmp_path, monkeypatch):
    fake = tmp_path / ("yt-dlp.exe" if sys.platform == "win32" else "yt-dlp")
    fake.write_bytes(b"x")
    monkeypatch.setenv("STREAMCLIP_YTDLP_PATH", str(fake))
    assert ytdlp_bin.ytdlp_argv() == (str(fake.resolve()),)


def test_ytdlp_argv_prefers_bundled_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("STREAMCLIP_YTDLP_PATH", raising=False)
    bundled = tmp_path / "bin" / "yt-dlp"
    bundled.mkdir(parents=True)
    name = "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp"
    exe = bundled / name
    exe.write_bytes(b"x")
    monkeypatch.setattr(ytdlp_bin, "app_root", lambda: tmp_path)
    monkeypatch.setattr(ytdlp_bin, "_bundle_dirs", lambda: [bundled])
    assert ytdlp_bin.ytdlp_argv() == (str(exe.resolve()),)


def test_build_ytdlp_cmd_uses_resolved_prefix(monkeypatch):
    from core.ingest.resolvers.url import _build_ytdlp_cmd
    from core.config import get_settings

    monkeypatch.setattr(
        "core.ingest.resolvers.url.ytdlp_argv",
        lambda: ("/tools/yt-dlp",),
    )
    cfg = get_settings()
    cmd = _build_ytdlp_cmd(
        "https://example.com/v",
        Path("out.mp4"),
        cfg,
        max_height=720,
        concurrent_fragments=1,
    )
    assert cmd[0] == "/tools/yt-dlp"
    assert "--no-playlist" in cmd

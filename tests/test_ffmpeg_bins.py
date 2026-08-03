"""Tests for bundled ffmpeg/ffprobe resolution (ADR-001 §4.5)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from core.config import get_settings
from core import ffmpeg_bins as fb


def test_ffmpeg_bin_prefers_explicit_path(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    fake = tmp_path / "custom-ffmpeg.exe"
    fake.write_bytes(b"")
    monkeypatch.setattr(cfg.ffmpeg, "ffmpeg_path", fake)
    monkeypatch.setattr(cfg.ffmpeg, "bin_dir", None)
    assert fb.ffmpeg_bin(cfg) == str(fake.resolve())


def test_ffmpeg_bin_uses_bin_dir(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    bin_dir = tmp_path / "ffmpeg"
    bin_dir.mkdir()
    exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    bundled = bin_dir / exe_name
    bundled.write_bytes(b"")
    monkeypatch.setattr(cfg.ffmpeg, "ffmpeg_path", None)
    monkeypatch.setattr(cfg.ffmpeg, "bin_dir", bin_dir)
    assert fb.ffmpeg_bin(cfg) == str(bundled.resolve())


def test_ffprobe_bin_uses_app_root_bundle(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    root = tmp_path / "app"
    bundle_dir = root / "bin" / "ffmpeg"
    bundle_dir.mkdir(parents=True)
    exe_name = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
    bundled = bundle_dir / exe_name
    bundled.write_bytes(b"")
    monkeypatch.setenv("STREAMCLIP_APP_ROOT", str(root))
    monkeypatch.setattr(cfg.ffmpeg, "ffprobe_path", None)
    monkeypatch.setattr(cfg.ffmpeg, "bin_dir", None)
    assert fb.ffprobe_bin(cfg) == str(bundled.resolve())


def test_app_root_honours_env(monkeypatch, tmp_path):
    monkeypatch.setenv("STREAMCLIP_APP_ROOT", str(tmp_path))
    assert fb.app_root() == tmp_path.resolve()


def test_ffmpeg_bin_finds_frozen_internal_layout(tmp_path, monkeypatch):
    """Packaged onedir puts bins under _internal/; cwd is the exe dir (no repo PATH)."""
    cfg = get_settings(reload=True)
    exe_dir = tmp_path / "sidecar"
    internal = exe_dir / "_internal" / "bin" / "ffmpeg"
    internal.mkdir(parents=True)
    exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    bundled = internal / exe_name
    bundled.write_bytes(b"")

    monkeypatch.chdir(exe_dir)  # real installs: cwd is sidecar dir, not the repo
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(exe_dir / "_internal"), raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "streamclip-sidecar.exe"))
    monkeypatch.delenv("STREAMCLIP_APP_ROOT", raising=False)
    monkeypatch.setattr(cfg.ffmpeg, "ffmpeg_path", None)
    monkeypatch.setattr(cfg.ffmpeg, "bin_dir", Path("bin/ffmpeg"))  # relative, missing next to exe
    monkeypatch.setattr(fb.shutil, "which", lambda _name: None)

    assert fb.ffmpeg_bin(cfg) == str(bundled.resolve())


def test_app_root_frozen_uses_meipass(tmp_path, monkeypatch):
    meipass = tmp_path / "_internal"
    meipass.mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "streamclip-sidecar.exe"))
    monkeypatch.delenv("STREAMCLIP_APP_ROOT", raising=False)
    assert fb.app_root() == meipass.resolve()


def test_ensure_tool_bins_on_path_prepends(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    bin_dir = tmp_path / "bin" / "ffmpeg"
    bin_dir.mkdir(parents=True)
    exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    bundled = bin_dir / exe_name
    bundled.write_bytes(b"")
    monkeypatch.setattr(cfg.ffmpeg, "ffmpeg_path", bundled)
    monkeypatch.setenv("PATH", str(tmp_path / "other"))
    asserted = fb.ensure_tool_bins_on_path(cfg)
    assert asserted == str(bin_dir.resolve())
    assert os.environ["PATH"].split(os.pathsep)[0] == str(bin_dir.resolve())

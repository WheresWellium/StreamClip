"""
Resolve the yt-dlp executable for server (PATH) and desktop (bundled / frozen).

Search order:
  1. Explicit ``STREAMCLIP_YTDLP_PATH`` env
  2. Bundled ``bin/yt-dlp/yt-dlp[.exe]`` under PyInstaller ``_MEIPASS``,
     the sidecar exe dir, and cwd (same relative layout as ffmpeg)
  3. ``shutil.which("yt-dlp")``
  4. ``[sys.executable, "-m", "yt_dlp"]`` when the module is importable
"""

from __future__ import annotations

import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path

from core.ffmpeg_bins import app_root

_EXE_SUFFIX = ".exe" if sys.platform == "win32" else ""


def _tool_name(base: str) -> str:
    return f"{base}{_EXE_SUFFIX}"


def _bundle_dirs() -> list[Path]:
    dirs: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            dirs.append(Path(meipass) / "bin" / "yt-dlp")
        exe_dir = Path(sys.executable).resolve().parent
        dirs.append(exe_dir / "bin" / "yt-dlp")
        dirs.append(exe_dir / "_internal" / "bin" / "yt-dlp")
    dirs.append(app_root() / "bin" / "yt-dlp")
    # Relative to process cwd — mirrors desktop.yaml ffmpeg.bin_dir style.
    dirs.append(Path("bin") / "yt-dlp")
    return dirs


@lru_cache(maxsize=1)
def ytdlp_argv() -> tuple[str, ...]:
    """Return argv prefix that invokes yt-dlp."""
    explicit = os.environ.get("STREAMCLIP_YTDLP_PATH")
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return (str(path.resolve()),)

    name = _tool_name("yt-dlp")
    for directory in _bundle_dirs():
        candidate = (directory / name).resolve()
        if candidate.is_file():
            return (str(candidate),)

    on_path = shutil.which("yt-dlp")
    if on_path:
        return (on_path,)

    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        return (name,)

    return (sys.executable, "-m", "yt_dlp")

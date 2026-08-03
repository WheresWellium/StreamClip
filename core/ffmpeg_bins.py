"""
Resolve ffmpeg/ffprobe executables for server (PATH) and desktop (bundled bin dir).

Search order:
  1. Explicit ``ffmpeg.ffmpeg_path`` / ``ffmpeg.ffprobe_path`` in config
  2. ``ffmpeg.bin_dir`` (contains ``ffmpeg.exe`` / ``ffprobe.exe``)
  3. Frozen layouts: ``sys._MEIPASS/bin/ffmpeg``, exe-dir, exe-dir/``_internal``
  4. ``{app_root}/bin/ffmpeg/`` (desktop bundle / repo layout)
  5. ``shutil.which`` on PATH
  6. Bare command name (``ffmpeg`` / ``ffprobe``)
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from core.config import Settings, get_settings

_EXE_SUFFIX = ".exe" if sys.platform == "win32" else ""


def _tool_name(base: str) -> str:
    return f"{base}{_EXE_SUFFIX}"


def app_root() -> Path:
    """Install / repo root for bundled assets (PyInstaller-safe).

    PyInstaller ≥6 one-dir places datas under ``_internal/`` (``sys._MEIPASS``),
    not beside the executable — match ``desktop_sidecar.run.app_root``.
    """
    env_root = os.environ.get("STREAMCLIP_APP_ROOT")
    if env_root:
        return Path(env_root).resolve()
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _bundle_tool_dirs(bundled_subdir: str) -> list[Path]:
    """Candidate dirs for bundled ffmpeg/ffprobe (dev + frozen layouts)."""
    dirs: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            dirs.append(Path(meipass) / bundled_subdir)
        exe_dir = Path(sys.executable).resolve().parent
        dirs.append(exe_dir / bundled_subdir)
        # PyInstaller ≥6 onedir without relying solely on _MEIPASS.
        dirs.append(exe_dir / "_internal" / bundled_subdir)
    dirs.append(app_root() / bundled_subdir)
    return dirs


def _resolve_tool(
    *,
    explicit: Path | None,
    bin_dir: Path | None,
    bundled_subdir: str,
    fallback_name: str,
) -> str:
    if explicit is not None:
        path = Path(explicit)
        if path.is_file():
            return str(path.resolve())

    search_dirs: list[Path] = []
    if bin_dir is not None:
        search_dirs.append(Path(bin_dir))
    search_dirs.extend(_bundle_tool_dirs(bundled_subdir))

    for directory in search_dirs:
        candidate = (directory / _tool_name(fallback_name)).resolve()
        if candidate.is_file():
            return str(candidate)

    on_path = shutil.which(fallback_name)
    if on_path:
        return on_path
    return _tool_name(fallback_name)


def ffmpeg_bin(cfg: Settings | None = None) -> str:
    settings = cfg or get_settings()
    return _resolve_tool(
        explicit=settings.ffmpeg.ffmpeg_path,
        bin_dir=settings.ffmpeg.bin_dir,
        bundled_subdir="bin/ffmpeg",
        fallback_name="ffmpeg",
    )


def ffprobe_bin(cfg: Settings | None = None) -> str:
    settings = cfg or get_settings()
    return _resolve_tool(
        explicit=settings.ffmpeg.ffprobe_path,
        bin_dir=settings.ffmpeg.bin_dir,
        bundled_subdir="bin/ffmpeg",
        fallback_name="ffprobe",
    )


def ensure_tool_bins_on_path(cfg: Settings | None = None) -> str | None:
    """Prepend the resolved ffmpeg directory to ``PATH``.

    librosa/audioread and some subprocess helpers look up ``ffmpeg`` on PATH
    rather than calling ``ffmpeg_bin()``. Without this, packaged installs with
    a scrubbed PATH lose audio-energy analysis even though the binary is bundled.
    Returns the directory that was prepended, or None if unresolved.
    """
    resolved = Path(ffmpeg_bin(cfg))
    if not resolved.is_file():
        return None
    bin_dir = str(resolved.parent.resolve())
    current = os.environ.get("PATH", "")
    parts = [p for p in current.split(os.pathsep) if p]
    if parts and Path(parts[0]).resolve() == Path(bin_dir):
        return bin_dir
    # Drop duplicate later entries so the bundled tools win.
    rest = [p for p in parts if Path(p).resolve() != Path(bin_dir)]
    os.environ["PATH"] = os.pathsep.join([bin_dir, *rest])
    return bin_dir

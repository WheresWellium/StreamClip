# Bundled ffmpeg for desktop builds (ADR-001 §4.5)

Place official builds here before packaging:

- Windows: `ffmpeg.exe`, `ffprobe.exe` — `scripts/download_ffmpeg_windows.ps1`
- macOS: `ffmpeg`, `ffprobe` (arm64) — `scripts/download_ffmpeg_macos.sh`
  (martin-riedl.de static arm64; not evermeet.cx — Intel-only)

The app resolves these via `core/ffmpeg_bins.py` — no PATH dependency when files exist.
Override with `STREAMCLIP_FFMPEG__BIN_DIR` or explicit paths in `config/desktop.yaml`.

# Bundled ffmpeg for desktop builds (ADR-001 §4.5)

Place official builds here before packaging:

- Windows: `ffmpeg.exe`, `ffprobe.exe`
- macOS/Linux: `ffmpeg`, `ffprobe`

Download: https://ffmpeg.org/download.html (use a static/GPL build for your target OS).

The app resolves these via `core/ffmpeg_bins.py` — no PATH dependency when files exist.
Override with `STREAMCLIP_FFMPEG__BIN_DIR` or explicit paths in `config/desktop.yaml`.

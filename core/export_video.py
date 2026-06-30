"""FFmpeg video encode arguments from ExportConfig."""

from __future__ import annotations

from core.config import ExportConfig

_NVENC_CODECS = frozenset({"h264_nvenc", "hevc_nvenc"})


def video_encode_args(cfg: ExportConfig, *, crf: int | None = None) -> list[str]:
    """
    Build ``-c:v`` and quality arguments for ffmpeg.

    NVENC uses ``-cq``; software codecs use ``-crf``.
    """
    codec = cfg.codec
    quality = crf if crf is not None else cfg.crf
    args: list[str] = ["-c:v", codec]

    if codec in _NVENC_CODECS:
        preset = cfg.preset if cfg.preset in ("ultrafast", "fast", "medium", "slow") else "fast"
        # Map x264 preset names to NVENC speed tiers
        nvenc_preset = {"ultrafast": "p1", "fast": "p4", "medium": "p5", "slow": "p7"}.get(
            preset, "p4",
        )
        args.extend(["-preset", nvenc_preset, "-cq", str(quality)])
    else:
        args.extend(["-crf", str(quality), "-preset", cfg.preset])

    args.extend(["-pix_fmt", cfg.pixel_format])
    return args


def audio_encode_args(cfg: ExportConfig) -> list[str]:
    return ["-c:a", "aac", "-b:a", cfg.audio_bitrate]


def output_fps_args(cfg: ExportConfig) -> list[str]:
    """Force output frame rate when configured (min 60 in config validation)."""
    if cfg.fps and cfg.fps > 0:
        return ["-r", str(cfg.fps)]
    return []

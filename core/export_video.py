"""FFmpeg video encode arguments from ExportConfig."""

from __future__ import annotations

from core.config import ExportConfig

_NVENC_CODECS = frozenset({"h264_nvenc", "hevc_nvenc"})
_VIDEOTOOLBOX_CODECS = frozenset({"h264_videotoolbox"})
_HW_EXPORT_CODECS = _NVENC_CODECS | _VIDEOTOOLBOX_CODECS


def _videotoolbox_q(crf: int) -> int:
    """Map x264-style CRF (0–51, lower=better) to VideoToolbox ``-q:v`` (1–100)."""
    return max(1, min(100, int(round(100 - (crf / 51.0) * 99))))


def video_encode_args(cfg: ExportConfig, *, crf: int | None = None) -> list[str]:
    """
    Build ``-c:v`` and quality arguments for ffmpeg.

    NVENC uses ``-cq``; VideoToolbox uses ``-q:v``; software codecs use ``-crf``.
    Resolves hardware codecs via ``effective_export_codec`` (§4.11 / §5.1).
    """
    from core.config import get_settings
    from core.gpu_profile import effective_export_codec

    codec = cfg.codec
    if codec in _HW_EXPORT_CODECS:
        codec = effective_export_codec(get_settings(), requested=codec)
    quality = crf if crf is not None else cfg.crf
    args: list[str] = ["-c:v", codec]

    if codec in _NVENC_CODECS:
        preset = cfg.preset if cfg.preset in ("ultrafast", "fast", "medium", "slow") else "fast"
        # Map x264 preset names to NVENC speed tiers
        nvenc_preset = {"ultrafast": "p1", "fast": "p4", "medium": "p5", "slow": "p7"}.get(
            preset, "p4",
        )
        args.extend(["-preset", nvenc_preset, "-cq", str(quality)])
    elif codec in _VIDEOTOOLBOX_CODECS:
        args.extend(["-q:v", str(_videotoolbox_q(quality))])
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

"""
GPU / NVENC detection and safe defaults (MASTER_TODO §4.11).

Desktop and Docker both default to CPU-safe encode paths in config files.
This module upgrades when hardware is present and downgrades when NVENC/CUDA
is configured but unavailable — preventing silent ffmpeg failures on first job.
"""

from __future__ import annotations

import os
import sys
import subprocess
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from core.config import Settings

log = structlog.get_logger(__name__)

_NVENC_CODECS = frozenset({"h264_nvenc", "hevc_nvenc"})


def is_darwin() -> bool:
    return sys.platform == "darwin"


def mps_available() -> bool:
    if not is_darwin():
        return False
    try:
        import torch

        return bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
    except Exception:
        return False


def cuda_available() -> bool:
    if is_darwin():
        return False
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def nvenc_available(cfg: Settings | None = None) -> bool:
    if is_darwin():
        return False
    from core.config import get_settings
    from core.ffmpeg_bins import ffmpeg_bin

    settings = cfg or get_settings()
    try:
        proc = subprocess.run(
            [ffmpeg_bin(settings), "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return proc.returncode == 0 and "h264_nvenc" in proc.stdout
    except Exception as exc:
        log.debug("nvenc_probe_failed", error=str(exc))
        return False


def effective_export_codec(cfg: Settings, *, requested: str | None = None) -> str:
    """Return an ffmpeg video codec guaranteed to work on this machine."""
    codec = requested if requested is not None else cfg.export.codec
    if codec in _NVENC_CODECS and not nvenc_available(cfg):
        log.warning("nvenc_unavailable_fallback", requested=codec, fallback="libx264")
        return "libx264"
    return codec


def effective_whisper_device(cfg: Settings) -> str:
    """Resolve whisper device, never returning cuda/MPS when absent."""
    device = cfg.whisper.device
    if device == "auto":
        if cuda_available():
            return "cuda"
        if mps_available():
            return "mps"
        return "cpu"
    if device == "cuda" and not cuda_available():
        log.warning("cuda_unavailable_fallback", requested=device, fallback="cpu")
        return "cpu"
    if device == "mps" and not mps_available():
        log.warning("mps_unavailable_fallback", requested=device, fallback="cpu")
        return "cpu"
    return device


def apply_gpu_env_defaults() -> None:
    """
    Set STREAMCLIP_* env overrides before the first ``get_settings()`` call.

    Uses ``setdefault`` for upgrades on desktop when GPU is present; uses
    unconditional ``os.environ[...]`` only to downgrade unsafe NVENC/CUDA
    requests when hardware is missing.
    """
    cuda = cuda_available()
    mps = mps_available()
    nvenc = nvenc_available() if cuda else False

    whisper_env = os.environ.get("STREAMCLIP_WHISPER__DEVICE", "")
    if whisper_env in ("", "auto"):
        if cuda:
            os.environ.setdefault("STREAMCLIP_WHISPER__DEVICE", "cuda")
        elif mps:
            os.environ.setdefault("STREAMCLIP_WHISPER__DEVICE", "mps")
        else:
            os.environ.setdefault("STREAMCLIP_WHISPER__DEVICE", "cpu")
    elif whisper_env == "cuda" and not cuda:
        os.environ["STREAMCLIP_WHISPER__DEVICE"] = "cpu"
    elif whisper_env == "mps" and not mps:
        os.environ["STREAMCLIP_WHISPER__DEVICE"] = "cpu"

    codec_env = os.environ.get("STREAMCLIP_EXPORT__CODEC", "")
    if codec_env in ("", "auto") and nvenc:
        os.environ.setdefault("STREAMCLIP_EXPORT__CODEC", "h264_nvenc")
    elif codec_env in _NVENC_CODECS and not nvenc:
        os.environ["STREAMCLIP_EXPORT__CODEC"] = "libx264"

    log.info(
        "gpu_profile",
        platform=sys.platform,
        cuda=cuda,
        mps=mps,
        nvenc=nvenc,
        whisper=os.environ.get("STREAMCLIP_WHISPER__DEVICE", "(config file)"),
        export_codec=os.environ.get("STREAMCLIP_EXPORT__CODEC", "(config file)"),
    )

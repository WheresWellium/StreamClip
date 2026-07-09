"""Tests for GPU/NVENC detection and safe fallbacks (MASTER_TODO §4.11)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.config import ExportConfig, Settings, WhisperConfig
from core.export_video import video_encode_args
from core.gpu_profile import (
    apply_gpu_env_defaults,
    cuda_available,
    effective_export_codec,
    effective_whisper_device,
    mps_available,
    nvenc_available,
)


def test_effective_whisper_device_cpu_when_cuda_missing():
    cfg = Settings(whisper=WhisperConfig(device="cuda"))
    with patch("core.gpu_profile.cuda_available", return_value=False):
        assert effective_whisper_device(cfg) == "cpu"


def test_effective_whisper_device_auto_picks_cpu_without_cuda():
    cfg = Settings(whisper=WhisperConfig(device="auto"))
    with patch("core.gpu_profile.cuda_available", return_value=False):
        assert effective_whisper_device(cfg) == "cpu"


def test_effective_export_codec_falls_back_from_nvenc():
    cfg = Settings(export=ExportConfig(codec="h264_nvenc"))
    with patch("core.gpu_profile.nvenc_available", return_value=False):
        assert effective_export_codec(cfg, requested="h264_nvenc") == "libx264"


def test_video_encode_args_uses_libx264_when_nvenc_missing():
    cfg = ExportConfig(codec="h264_nvenc")
    settings = Settings(export=cfg)
    with patch("core.config.get_settings", return_value=settings), patch(
        "core.gpu_profile.nvenc_available", return_value=False
    ):
        args = video_encode_args(cfg)
    assert "-c:v" in args
    assert args[args.index("-c:v") + 1] == "libx264"


def test_apply_gpu_env_defaults_downgrades_unsafe_nvenc(monkeypatch):
    monkeypatch.delenv("STREAMCLIP_EXPORT__CODEC", raising=False)
    monkeypatch.setenv("STREAMCLIP_EXPORT__CODEC", "h264_nvenc")
    with patch("core.gpu_profile.cuda_available", return_value=False), patch(
        "core.gpu_profile.nvenc_available", return_value=False
    ):
        apply_gpu_env_defaults()
    import os

    assert os.environ["STREAMCLIP_EXPORT__CODEC"] == "libx264"


def test_effective_whisper_device_auto_picks_mps_on_darwin():
    cfg = Settings(whisper=WhisperConfig(device="auto"))
    with patch("core.gpu_profile.cuda_available", return_value=False), patch(
        "core.gpu_profile.mps_available", return_value=True
    ):
        assert effective_whisper_device(cfg) == "mps"


def test_nvenc_unavailable_on_darwin():
    with patch("core.gpu_profile.is_darwin", return_value=True):
        assert nvenc_available(Settings()) is False


def test_cuda_unavailable_on_darwin():
    with patch("core.gpu_profile.is_darwin", return_value=True), patch(
        "core.gpu_profile.torch", create=True
    ):
        assert cuda_available() is False


def test_apply_gpu_env_defaults_never_nvenc_on_darwin(monkeypatch):
    monkeypatch.delenv("STREAMCLIP_EXPORT__CODEC", raising=False)
    monkeypatch.delenv("STREAMCLIP_WHISPER__DEVICE", raising=False)
    with patch("core.gpu_profile.is_darwin", return_value=True), patch(
        "core.gpu_profile.cuda_available", return_value=False
    ), patch("core.gpu_profile.mps_available", return_value=True), patch(
        "core.gpu_profile.nvenc_available", return_value=False
    ):
        apply_gpu_env_defaults()
    import os

    assert os.environ.get("STREAMCLIP_WHISPER__DEVICE") == "mps"
    assert os.environ.get("STREAMCLIP_EXPORT__CODEC", "libx264") != "h264_nvenc"


def test_nvenc_available_parses_ffmpeg_encoders():
    proc = MagicMock(returncode=0, stdout=" V..... h264_nvenc\n")
    with patch("core.gpu_profile.subprocess.run", return_value=proc):
        assert nvenc_available(Settings()) is True


def test_cuda_available_handles_missing_torch():
    with patch.dict("sys.modules", {"torch": None}):
        assert cuda_available() is False


def test_mps_available_success_on_darwin():
    fake_torch = MagicMock()
    fake_torch.backends.mps.is_available.return_value = True
    with patch("core.gpu_profile.is_darwin", return_value=True), patch.dict(
        "sys.modules", {"torch": fake_torch}
    ):
        assert mps_available() is True


def test_mps_available_import_error():
    with patch("core.gpu_profile.is_darwin", return_value=True), patch.dict(
        "sys.modules", {"torch": None}
    ):
        assert mps_available() is False


def test_nvenc_probe_exception_returns_false():
    with patch("core.gpu_profile.subprocess.run", side_effect=OSError("no ffmpeg")):
        assert nvenc_available(Settings()) is False


def test_effective_whisper_auto_picks_cuda():
    cfg = Settings(whisper=WhisperConfig(device="auto"))
    with patch("core.gpu_profile.cuda_available", return_value=True), patch(
        "core.gpu_profile.mps_available", return_value=False
    ):
        assert effective_whisper_device(cfg) == "cuda"


def test_effective_whisper_mps_fallback_to_cpu():
    cfg = Settings(whisper=WhisperConfig(device="mps"))
    with patch("core.gpu_profile.mps_available", return_value=False):
        assert effective_whisper_device(cfg) == "cpu"


def test_apply_gpu_env_defaults_upgrade_cuda_and_nvenc(monkeypatch):
    monkeypatch.delenv("STREAMCLIP_WHISPER__DEVICE", raising=False)
    monkeypatch.delenv("STREAMCLIP_EXPORT__CODEC", raising=False)
    with patch("core.gpu_profile.cuda_available", return_value=True), patch(
        "core.gpu_profile.mps_available", return_value=False
    ), patch("core.gpu_profile.nvenc_available", return_value=True):
        apply_gpu_env_defaults()
    import os

    assert os.environ.get("STREAMCLIP_WHISPER__DEVICE") == "cuda"
    assert os.environ.get("STREAMCLIP_EXPORT__CODEC") == "h264_nvenc"


def test_apply_gpu_env_defaults_downgrade_explicit_cuda(monkeypatch):
    monkeypatch.setenv("STREAMCLIP_WHISPER__DEVICE", "cuda")
    with patch("core.gpu_profile.cuda_available", return_value=False), patch(
        "core.gpu_profile.mps_available", return_value=False
    ), patch("core.gpu_profile.nvenc_available", return_value=False):
        apply_gpu_env_defaults()
    import os

    assert os.environ["STREAMCLIP_WHISPER__DEVICE"] == "cpu"

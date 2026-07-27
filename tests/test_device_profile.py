"""Device profile + storage status for desktop setup."""

from __future__ import annotations

from pathlib import Path

from core.config import get_settings
from core.device_profile import build_device_profile, build_storage_status


def test_build_device_profile_has_recommendation(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.storage, "backend", "local")
    monkeypatch.setattr(cfg.storage, "local_root", str(tmp_path / "storage"))
    profile = build_device_profile(cfg)
    assert profile.cpu_cores >= 1
    assert profile.disk_free_gb >= 0
    assert profile.processing_mode in {"cpu", "gpu_cuda", "gpu_nvenc", "apple_silicon"}
    assert profile.recommendation
    assert Path(profile.disk_path).exists()


def test_build_storage_status_local(tmp_path, monkeypatch):
    root = tmp_path / "storage"
    root.mkdir()
    (root / "clip.bin").write_bytes(b"abc")
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.storage, "backend", "local")
    monkeypatch.setattr(cfg.storage, "local_root", str(root))
    status = build_storage_status(cfg)
    assert status["backend"] == "local"
    assert status["label"] == "Saved on this device"
    assert status["used_bytes"] == 3
    assert status["free_bytes"] is not None and status["free_bytes"] > 0
    assert status["advanced"] is False


def test_build_storage_status_external(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.storage, "backend", "minio")
    status = build_storage_status(cfg)
    assert status["backend"] == "minio"
    assert status["advanced"] is True
    assert status["root"] is None

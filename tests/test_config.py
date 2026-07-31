"""Config loading tests."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from core.config import Settings, get_settings


def test_env_overrides_yaml(monkeypatch, tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("whisper:\n  model_size: large-v3\n  device: auto\n  compute_type: float16\n")
    monkeypatch.setenv("STREAMCLIP_WHISPER__MODEL_SIZE", "tiny")
    monkeypatch.setenv("STREAMCLIP_WHISPER__DEVICE", "cpu")
    monkeypatch.setenv("STREAMCLIP_WHISPER__COMPUTE_TYPE", "int8")
    cfg = get_settings(cfg_file, reload=True)
    assert cfg.whisper.model_size == "tiny"
    assert cfg.whisper.device == "cpu"
    assert cfg.whisper.compute_type == "int8"


def test_ensure_dirs_relocates_unwritable_output(tmp_path, monkeypatch):
    """Program Files-style installs must not crash when 'output' is not writable."""
    monkeypatch.setenv("STREAMCLIP_DESKTOP_DATA_DIR", str(tmp_path / "userdata"))
    cfg = Settings(
        workspace_dir=tmp_path / "workspace",
        output_dir=tmp_path / "locked" / "output",
        cache_dir=tmp_path / "cache",
    )
    locked = tmp_path / "locked"
    locked.mkdir()

    real_mkdir = Path.mkdir

    def guarded_mkdir(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        # Refuse creating anything under the locked prefix.
        try:
            self.resolve().relative_to(locked.resolve())
            raise PermissionError(5, "Access is denied", str(self))
        except ValueError:
            return real_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", guarded_mkdir):
        cfg.ensure_dirs()

    assert cfg.output_dir == (tmp_path / "userdata" / "output").resolve()
    assert cfg.output_dir.is_dir()
    assert (tmp_path / "workspace").is_dir()
    assert (tmp_path / "cache").is_dir()


# ── Systemic guardrails: every writable path must be registered + relocatable ──
# These stop the recurring "relative path under a read-only install prefix" bug
# (root cause of the white screen and the license 500) from returning.

_EXPECTED_WRITABLE_SLOTS = {
    "workspace_dir",
    "output_dir",
    "cache_dir",
    "storage.local_root",
    "licensing.license_file",
}


def test_writable_slots_registry_is_complete():
    """If a new writable path is added, it must be registered here consciously."""
    cfg = Settings()
    labels = {label for label, _p, _f, _r in cfg._writable_slots()}
    assert labels == _EXPECTED_WRITABLE_SLOTS


def _guarded_mkdir_under(locked: Path):
    real_mkdir = Path.mkdir

    def guarded(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            self.resolve().relative_to(locked.resolve())
            raise PermissionError(5, "Access is denied", str(self))
        except ValueError:
            return real_mkdir(self, *args, **kwargs)

    return guarded


def test_ensure_dirs_relocates_every_writable_slot(tmp_path, monkeypatch):
    """All writable slots — dirs and the license file — relocate off a read-only
    prefix, not just output_dir."""
    monkeypatch.setenv("STREAMCLIP_DESKTOP_DATA_DIR", str(tmp_path / "userdata"))
    locked = tmp_path / "locked"
    locked.mkdir()
    cfg = Settings(
        workspace_dir=locked / "workspace",
        output_dir=locked / "output",
        cache_dir=locked / "cache",
        storage={"local_root": locked / "storage"},
        licensing={"license_file": locked / "lic" / "license.json"},
    )

    with patch.object(Path, "mkdir", _guarded_mkdir_under(locked)):
        cfg.ensure_dirs()

    root = (tmp_path / "userdata").resolve()
    assert cfg.workspace_dir == root / "workspace"
    assert cfg.output_dir == root / "output"
    assert cfg.cache_dir == root / "cache"
    assert cfg.storage.local_root == root / "storage"
    assert cfg.licensing.license_file == root / "lic" / "license.json"
    assert cfg.licensing.license_file.parent.is_dir()


def test_verify_writable_reports_unwritable_slot(tmp_path):
    """verify_writable surfaces a clear, per-slot failure list."""
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file", encoding="utf-8")  # parent-is-a-file → OSError
    cfg = Settings(
        workspace_dir=tmp_path / "ws",
        output_dir=blocker / "output",
        cache_dir=tmp_path / "cache",
        storage={"local_root": tmp_path / "storage"},
        licensing={"license_file": tmp_path / "lic" / "license.json"},
    )
    failures = cfg.verify_writable()
    assert any("output_dir" in f for f in failures)
    assert all("workspace_dir" not in f for f in failures)

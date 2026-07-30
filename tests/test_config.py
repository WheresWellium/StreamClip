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

"""Config loading tests."""

from __future__ import annotations

import os

from core.config import get_settings


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

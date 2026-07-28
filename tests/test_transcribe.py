"""Whisper CPU config coercion."""

from __future__ import annotations

import pytest

from core.config import WhisperConfig
from core.transcribe import _get_model


@pytest.mark.parametrize("compute_type", ["float16", "int8_float16"])
def test_cpu_coerces_gpu_compute_types_to_int8(monkeypatch, compute_type):
    monkeypatch.setattr("core.transcribe._model_cache", {})
    monkeypatch.setattr("core.gpu_profile.effective_whisper_device", lambda _cfg: "cpu")

    class FakeWhisper:
        def __init__(self, model, device, compute_type):
            self.args = (model, device, compute_type)

    monkeypatch.setattr("core.transcribe.WhisperModel", FakeWhisper)
    cfg = WhisperConfig(model_size="tiny", device="cpu", compute_type=compute_type)
    model = _get_model(cfg)
    assert model.args == ("tiny", "cpu", "int8")

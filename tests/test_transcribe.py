"""Whisper CPU config coercion."""

from __future__ import annotations

from core.config import WhisperConfig
from core.transcribe import _get_model


def test_cpu_coerces_float16_to_int8(monkeypatch):
    monkeypatch.setattr("core.transcribe._model_cache", {})
    monkeypatch.setattr("core.gpu_profile.effective_whisper_device", lambda _cfg: "cpu")

    class FakeWhisper:
        def __init__(self, model, device, compute_type):
            self.args = (model, device, compute_type)

    monkeypatch.setattr("core.transcribe.WhisperModel", FakeWhisper)
    cfg = WhisperConfig(model_size="tiny", device="cpu", compute_type="float16")
    model = _get_model(cfg)
    assert model.args == ("tiny", "cpu", "int8")

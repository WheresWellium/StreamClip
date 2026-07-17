"""Line-coverage sweep for pure-function core modules (MASTER_TODO 3.10)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from core.config import CaptionConfig, HighlightConfig, ReframeConfig, Settings
from core.models import ProcessedClip, TranscriptSegment, VideoMeta, Word


# ─── models.py properties (45, 67, 159, 181, 185) ─────────────────────────────

def test_model_properties():
    w = Word(text="hi", start=1.0, end=1.5, probability=0.9)
    assert w.duration == pytest.approx(0.5)

    seg = TranscriptSegment(id=0, text="hi there", start=0.0, end=2.0, words=(w, w))
    assert seg.words_per_second == pytest.approx(2 / 2.0)

    pc = ProcessedClip.__new__(ProcessedClip)
    pc.final_path = Path("/out/final.mp4")
    assert pc.filename == "final.mp4"

    meta = VideoMeta(
        path=Path("/x.mp4"), url=None, title="t", duration=10.0,
        width=1920, height=1080, fps=30.0, size_bytes=1, has_audio=True,
        video_codec="h264", audio_codec="aac",
    )
    assert meta.aspect_ratio == pytest.approx(1920 / 1080)
    assert meta.is_vertical is False

    vertical = VideoMeta(
        path=Path("/y.mp4"), url=None, title="t", duration=10.0,
        width=1080, height=1920, fps=30.0, size_bytes=1, has_audio=True,
        video_codec="h264", audio_codec="aac",
    )
    assert vertical.is_vertical is True


# ─── url_normalize.py (44, 58) ────────────────────────────────────────────────

def test_url_normalize_missing_host():
    from core.ingest.url_normalize import normalize_source_url

    with pytest.raises(ValueError):
        normalize_source_url("https://")


def test_url_normalize_keeps_nonstandard_port():
    from core.ingest.url_normalize import normalize_source_url

    out = normalize_source_url("https://youtube.com:8443/watch?v=abc")
    assert "youtube.com:8443" in out


# ─── peak_detection.py (43-44, 89) ────────────────────────────────────────────

def test_find_peaks_merges_close_peaks_keeping_higher():
    from core.peak_detection import find_peak_indices, windows_from_peaks

    # Two peaks within min_distance; the later, higher one replaces the earlier.
    values = np.array([0.0, 0.6, 0.0, 0.9, 0.0])
    peaks = find_peak_indices(values, min_height=0.5, min_distance=5)
    assert peaks == [3]

    # A wide padding forces the max_duration clamp (89).
    windows = windows_from_peaks(
        [50.0], padding_secs=100.0, min_duration=5.0, max_duration=30.0,
        source_duration=1000.0,
    )
    assert windows and (windows[0][1] - windows[0][0]) <= 30.0


# ─── eta.py (75, 95) ──────────────────────────────────────────────────────────

def test_eta_stage_seconds_branches():
    from core.config import get_settings
    from core.eta import estimate_stage_seconds

    cfg = get_settings()
    common = dict(
        source_kind="upload", target_clips=5, skip_optical_flow=False, cfg=cfg,
    )
    # upload ingest without a file size -> duration-based floor (75)
    up = estimate_stage_seconds(stage="ingest", duration_secs=600.0, file_size_bytes=None, **common)
    assert up >= 30.0

    # unknown stage -> default (95)
    assert estimate_stage_seconds(stage="mystery", duration_secs=1.0, **common) == 60.0


# ─── config.py validators + loaders (75, 93, 119, 379-381, 406) ──────────────

def test_config_validators_reject_bad_values():
    with pytest.raises(ValueError):
        HighlightConfig(
            weight_llm_virality=0.9,
            weight_audio_energy=0.9,
            weight_spectral_novelty=0.0,
            weight_optical_flow=0.0,
            weight_chat_spikes=0.0,
        )
    with pytest.raises(ValueError):
        ReframeConfig(preset="not-a-preset")
    with pytest.raises(ValueError):
        CaptionConfig(style="not-a-style")


def test_settings_from_yaml(tmp_path):
    p = tmp_path / "cfg.yaml"
    p.write_text("log_level: WARNING\nlog_json: true\n", encoding="utf-8")
    cfg = Settings.from_yaml(p)
    assert cfg.log_level == "WARNING"
    assert cfg.log_json is True


def test_get_settings_missing_file_uses_env_only():
    from core.config import get_settings

    try:
        cfg = get_settings(yaml_path=str(Path("/nonexistent-config-xyz.yaml")), reload=True)
        assert isinstance(cfg, Settings)
    finally:
        # Restore the canonical (config.yaml-backed) settings for later tests.
        get_settings(reload=True)


# ─── virality.py client construction + call paths (223-224, 252-258) ──────────

def test_virality_build_client_ollama():
    from core.config import LLMConfig
    from core.virality import _build_client

    client = _build_client(LLMConfig(provider="ollama", base_url="http://127.0.0.1:11434"))
    assert client is not None


def test_virality_build_client_openai():
    from core.config import LLMConfig
    from core.virality import _build_client

    client = _build_client(LLMConfig(provider="openai", api_key="sk-test"))
    assert client is not None


def test_virality_build_client_anthropic():
    from core.config import LLMConfig
    from core.virality import _build_client

    client = _build_client(LLMConfig(provider="anthropic", api_key="sk-test"))
    assert client is not None


def test_virality_build_client_unknown_raises():
    from core.config import LLMConfig
    from core.virality import _build_client

    cfg = LLMConfig()
    object.__setattr__(cfg, "provider", "bogus")
    with pytest.raises(ValueError):
        _build_client(cfg)


def test_virality_call_llm_openai_path():
    from core.config import LLMConfig
    from core.virality import _call_llm

    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = '{"score": 5}'
    client = MagicMock()
    client.chat.completions.create.return_value = resp

    out = _call_llm(client, LLMConfig(provider="openai"), "prompt")
    assert out == '{"score": 5}'


def test_virality_call_llm_anthropic_path():
    from core.config import LLMConfig
    from core.virality import _call_llm

    resp = MagicMock()
    resp.content = [MagicMock()]
    resp.content[0].text = '{"score": 7}'
    client = MagicMock()
    client.messages.create.return_value = resp

    out = _call_llm(client, LLMConfig(provider="anthropic"), "prompt")
    assert out == '{"score": 7}'

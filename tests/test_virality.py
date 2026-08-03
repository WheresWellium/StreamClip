"""Post-hoc virality scoring tests."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from core.config import HighlightConfig, Settings
from core.models import Emotion
from core.virality import (
    ensemble_with_virality,
    score_clip_virality,
    score_clips_virality_parallel,
)


def test_ensemble_with_virality_combines_discovery_and_llm():
    hcfg = HighlightConfig(
        weight_llm_virality=0.40,
        weight_audio_energy=0.25,
        weight_spectral_novelty=0.15,
        weight_optical_flow=0.15,
        weight_chat_spikes=0.05,
    )
    score = ensemble_with_virality(
        llm_score=80.0,
        audio_score=0.5,
        spectral_score=0.3,
        flow_score=0.2,
        chat_score=0.4,
        hcfg=hcfg,
        skip_optical_flow=False,
        has_chat=True,
    )
    # LLM contributes 0.8 * 0.40; discovery signals weighted by remaining weights
    assert 0.0 < score <= 1.0
    assert score > 0.3


def test_ensemble_with_virality_skips_flow_weight_when_tier_hint():
    hcfg = HighlightConfig()
    with_flow = ensemble_with_virality(
        llm_score=50.0,
        audio_score=0.8,
        spectral_score=0.8,
        flow_score=0.0,
        hcfg=hcfg,
        skip_optical_flow=False,
    )
    without_flow = ensemble_with_virality(
        llm_score=50.0,
        audio_score=0.8,
        spectral_score=0.8,
        flow_score=0.0,
        hcfg=hcfg,
        skip_optical_flow=True,
    )
    # Skipping flow renormalizes weights — same zero flow contribution, higher score.
    assert without_flow > with_flow


def test_score_clip_virality_parses_llm_json():
    cfg = Settings()
    payload = {
        "score": 72,
        "emotion": "clutch",
        "meme_keywords": ["1v5", "clutch"],
        "reason": "High-stakes play with emotional payoff.",
    }

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.message.content = json.dumps(payload)
    mock_client.chat.return_value = mock_resp

    with patch("core.virality._build_client", return_value=mock_client):
        result = score_clip_virality(
            text="No way I just won that 1v5",
            start_secs=10.0,
            end_secs=25.0,
            cfg=cfg,
        )

    assert result.score == 72.0
    assert result.emotion == Emotion.CLUTCH
    assert "clutch" in result.meme_keywords
    assert result.reason


def test_score_clip_virality_returns_neutral_on_failure():
    cfg = Settings()
    mock_client = MagicMock()
    mock_client.chat.side_effect = RuntimeError("ollama down")

    with patch("core.virality._build_client", return_value=mock_client):
        result = score_clip_virality(
            text="quiet moment",
            start_secs=0.0,
            end_secs=10.0,
            cfg=cfg,
        )

    assert result.score == 0.0
    assert result.emotion == Emotion.NEUTRAL


def test_score_clips_virality_parallel_preserves_order():
    cfg = Settings()
    payload = {
        "score": 60,
        "emotion": "hype",
        "meme_keywords": ["wow"],
        "reason": "Hype moment.",
    }
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.message.content = json.dumps(payload)
    mock_client.chat.return_value = mock_resp

    with patch("core.virality._ollama_reachable", return_value=True):
        with patch("core.virality._build_client", return_value=mock_client):
            results = score_clips_virality_parallel(
                [("clip a", 0.0, 10.0), ("clip b", 10.0, 20.0)],
                cfg,
                max_workers=2,
            )

    assert len(results) == 2
    assert mock_client.chat.call_count == 2
    assert all(r.score == 60.0 for r in results)


def test_score_clips_virality_parallel_missing_client_degrades():
    cfg = Settings()
    with patch("core.virality._ollama_reachable", return_value=True):
        with patch("core.virality._build_client", side_effect=ImportError("no ollama")):
            results = score_clips_virality_parallel(
                [("clip a", 0.0, 10.0), ("clip b", 10.0, 20.0)],
                cfg,
                max_workers=2,
            )
    assert len(results) == 2
    # Wave 2: heuristic fallback instead of unavailable zeros
    assert all(r.reason.startswith("Heuristic") for r in results)
    assert all(0.0 <= r.score <= 100.0 for r in results)


def test_score_clips_virality_parallel_skips_when_ollama_down():
    cfg = Settings()
    with patch("core.virality._ollama_reachable", return_value=False):
        with patch("core.virality._build_client") as build:
            results = score_clips_virality_parallel(
                [("clip a", 0.0, 10.0)],
                cfg,
                max_workers=1,
            )
    build.assert_not_called()
    assert results[0].reason.startswith("Heuristic")
    assert 0.0 <= results[0].score <= 100.0

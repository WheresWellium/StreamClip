"""Profile-aware prompt building and scoring-context tests."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from core.chat_spikes import ChatEvent
from core.config import Settings
from core.virality import (
    ClipScoringContext,
    build_virality_prompt,
    score_clips_virality_parallel,
    select_chat_excerpts,
)
from backend.services.feedback_service import APPROVAL_IMPLICIT_RATING


# ─── Prompt building ──────────────────────────────────────────────────────────

def test_prompt_defaults_to_general_persona():
    prompt = build_virality_prompt(text="hello", start=0, end=10, duration=10)
    assert "short-form video strategist" in prompt
    assert "SIGNAL TELEMETRY" not in prompt
    assert "LIVE CHAT" not in prompt
    assert "SURROUNDING TRANSCRIPT" not in prompt


def test_prompt_uses_profile_persona():
    ctx = ClipScoringContext(content_profile="podcast")
    prompt = build_virality_prompt(text="x", start=0, end=10, duration=10, context=ctx)
    assert "podcast growth editor" in prompt
    assert "Contrarian or surprising claims" in prompt
    # Gaming criteria must not leak into podcast scoring
    assert "Kill streaks" not in prompt


def test_prompt_unknown_profile_falls_back_to_general():
    ctx = ClipScoringContext(content_profile="does-not-exist")
    prompt = build_virality_prompt(text="x", start=0, end=10, duration=10, context=ctx)
    assert "short-form video strategist" in prompt


def test_prompt_includes_signal_telemetry():
    ctx = ClipScoringContext(audio_score=0.92, chat_score=0.88)
    prompt = build_virality_prompt(text="x", start=0, end=10, duration=10, context=ctx)
    assert "SIGNAL TELEMETRY" in prompt
    assert "Audio energy: 0.92" in prompt
    assert "Chat spike: 0.88" in prompt
    # Signals not provided are omitted entirely
    assert "Visual motion" not in prompt


def test_prompt_includes_chat_and_surrounding_context():
    ctx = ClipScoringContext(
        chat_excerpts=("OMEGALUL", "NO WAY"),
        text_before="setup line",
        text_after="payoff line",
    )
    prompt = build_virality_prompt(text="x", start=0, end=10, duration=10, context=ctx)
    assert "LIVE CHAT DURING CLIP" in prompt
    assert "• OMEGALUL" in prompt
    assert 'Before: "setup line"' in prompt
    assert 'After: "payoff line"' in prompt


def test_prompt_always_ends_with_json_contract():
    prompt = build_virality_prompt(text="x", start=0, end=10, duration=10)
    assert '"score": <integer 0–100>' in prompt
    assert prompt.rstrip().endswith("}")


# ─── Chat excerpt selection ───────────────────────────────────────────────────

def test_select_chat_excerpts_filters_window_and_truncates():
    events = [
        ChatEvent(offset_secs=5.0, text="before"),
        ChatEvent(offset_secs=12.0, text="A" * 200),
        ChatEvent(offset_secs=18.0, text="  inside  "),
        ChatEvent(offset_secs=25.0, text="after"),
    ]
    out = select_chat_excerpts(events, 10.0, 20.0)
    assert out == ("A" * 80, "inside")


def test_select_chat_excerpts_samples_evenly_when_over_limit():
    events = [ChatEvent(offset_secs=float(i), text=f"m{i}") for i in range(100)]
    out = select_chat_excerpts(events, 0.0, 100.0, limit=10)
    assert len(out) == 10
    assert out[0] == "m0"
    # Sampled across the whole window, not just the head
    assert any(int(m[1:]) > 50 for m in out)


def test_select_chat_excerpts_empty():
    assert select_chat_excerpts([], 0.0, 10.0) == ()


# ─── Parallel scoring with contexts ───────────────────────────────────────────

def _mock_llm_client(score: int = 50) -> MagicMock:
    payload = {"score": score, "emotion": "hype", "meme_keywords": [], "reason": "r"}
    client = MagicMock()
    resp = MagicMock()
    resp.message.content = json.dumps(payload)
    client.chat.return_value = resp
    return client


def test_parallel_scoring_accepts_aligned_contexts():
    cfg = Settings()
    contexts = [
        ClipScoringContext(content_profile="gaming"),
        ClipScoringContext(content_profile="podcast"),
    ]
    client = _mock_llm_client()
    with patch("core.virality._ollama_reachable", return_value=True):
        with patch("core.virality._build_client", return_value=client):
            results = score_clips_virality_parallel(
                [("a", 0.0, 10.0), ("b", 10.0, 20.0)],
                cfg,
                contexts=contexts,
                max_workers=1,
            )
    assert len(results) == 2
    prompts = [c.kwargs["messages"][0]["content"] for c in client.chat.call_args_list]
    assert any("gaming content strategist" in p for p in prompts)
    assert any("podcast growth editor" in p for p in prompts)


def test_parallel_scoring_rejects_misaligned_contexts():
    cfg = Settings()
    with pytest.raises(ValueError, match="align 1:1"):
        score_clips_virality_parallel(
            [("a", 0.0, 10.0)],
            cfg,
            contexts=[None, None],
        )


# ─── Implicit approval feedback ───────────────────────────────────────────────

def test_approval_implicit_rating_mapping():
    assert APPROVAL_IMPLICIT_RATING["approved"] == 5
    assert APPROVAL_IMPLICIT_RATING["rejected"] == 1
    assert "draft" not in APPROVAL_IMPLICIT_RATING

"""Deterministic heuristic virality fallback tests."""

from __future__ import annotations

from unittest.mock import patch

from core.config import Settings
from core.models import Emotion
from core.virality import (
    UNAVAILABLE_REASON,
    ViralityResult,
    derive_virality_source,
    score_clips_virality_parallel,
)
from core.virality_heuristic import HEURISTIC_REASON, heuristic_virality_score


def test_heuristic_score_is_deterministic():
    kwargs = dict(
        text="No way chat look at this clutch, let's go!",
        start_secs=10.0,
        end_secs=35.0,
        audio_score=0.7,
        chat_score=0.5,
    )
    a = heuristic_virality_score(**kwargs)
    b = heuristic_virality_score(**kwargs)
    assert a == b
    assert a.reason.startswith(HEURISTIC_REASON)
    assert "hooks" in a.reason


def test_heuristic_score_bounds_0_100():
    for text, start, end, audio, chat in (
        ("", 0.0, 1.0, None, None),
        ("lol haha funny", 0.0, 5.0, 1.0, 1.0),
        ("oh my god no way watch this insane clutch!!!", 0.0, 30.0, 1.0, 1.0),
        ("quiet", 0.0, 400.0, 0.0, 0.0),
    ):
        result = heuristic_virality_score(
            text=text,
            start_secs=start,
            end_secs=end,
            audio_score=audio,
            chat_score=chat,
        )
        assert 0.0 <= result.score <= 100.0


def test_heuristic_rewards_hooks_and_sweet_spot_duration():
    flat = heuristic_virality_score(
        text="um okay so then we went",
        start_secs=0.0,
        end_secs=30.0,
    )
    spicy = heuristic_virality_score(
        text="Oh my god no way watch this!!! lol haha",
        start_secs=0.0,
        end_secs=30.0,
    )
    assert spicy.score > flat.score


def test_heuristic_duration_edges_stay_in_bounds():
    tiny = heuristic_virality_score(text="hi", start_secs=0.0, end_secs=2.0)
    long = heuristic_virality_score(text="hi there everyone", start_secs=0.0, end_secs=200.0)
    mid_short = heuristic_virality_score(text="hi there", start_secs=0.0, end_secs=12.0)
    mid_long = heuristic_virality_score(text="hi there", start_secs=0.0, end_secs=70.0)
    for result in (tiny, long, mid_short, mid_long):
        assert 0.0 <= result.score <= 100.0


def test_clip_out_exposes_virality_source():
    from backend.api.schemas import ClipOut

    base = dict(
        id="c1",
        rank=1,
        title="t",
        hook="h",
        emotion="hype",
        start_secs=0.0,
        end_secs=10.0,
        duration_secs=10.0,
        ensemble_score=0.5,
        audio_score=0.1,
        spectral_score=0.1,
        flow_score=0.1,
        status="done",
        render_time_secs=1.0,
        file_size_bytes=1,
    )
    assert ClipOut(llm_score=70.0, llm_reason="Strong hook.", **base).virality_source == "llm"
    assert ClipOut(
        llm_score=40.0, llm_reason=HEURISTIC_REASON, **base
    ).virality_source == "heuristic"
    assert ClipOut(
        llm_score=0.0, llm_reason=UNAVAILABLE_REASON, **base
    ).virality_source == "unavailable"


def test_derive_virality_source_from_reason_convention():
    assert derive_virality_source(HEURISTIC_REASON, 55.0) == "heuristic"
    assert derive_virality_source(UNAVAILABLE_REASON, 0.0) == "unavailable"
    assert derive_virality_source("Strong hook and payoff.", 72.0) == "llm"
    assert derive_virality_source("", 0.0) == "unavailable"


def test_parallel_uses_heuristic_when_ollama_down():
    cfg = Settings()
    with patch("core.virality._ollama_reachable", return_value=False):
        with patch("core.virality._build_client") as build:
            results = score_clips_virality_parallel(
                [("Oh my god no way!!!", 0.0, 25.0)],
                cfg,
                max_workers=1,
            )
    build.assert_not_called()
    assert len(results) == 1
    assert results[0].reason.startswith(HEURISTIC_REASON)
    assert results[0].score > 0.0
    assert derive_virality_source(results[0].reason, results[0].score) == "heuristic"


def test_parallel_uses_heuristic_when_client_missing():
    cfg = Settings()
    with patch("core.virality._ollama_reachable", return_value=True):
        with patch("core.virality._build_client", side_effect=ImportError("no ollama")):
            results = score_clips_virality_parallel(
                [("clip a", 0.0, 10.0), ("clip b lol", 10.0, 30.0)],
                cfg,
                max_workers=2,
            )
    assert len(results) == 2
    assert all(r.reason.startswith(HEURISTIC_REASON) for r in results)
    assert all(0.0 <= r.score <= 100.0 for r in results)


def test_parallel_falls_back_when_per_clip_llm_fails():
    cfg = Settings()
    unavailable = ViralityResult(
        score=0.0,
        emotion=Emotion.NEUTRAL,
        reason=UNAVAILABLE_REASON,
        meme_keywords=[],
    )
    with patch("core.virality._ollama_reachable", return_value=True):
        with patch("core.virality._build_client", return_value=object()):
            with patch("core.virality.score_clip_virality", return_value=unavailable):
                results = score_clips_virality_parallel(
                    [("No way chat!!!", 0.0, 28.0)],
                    cfg,
                    max_workers=1,
                )
    assert results[0].reason.startswith(HEURISTIC_REASON)
    assert results[0].score > 0.0

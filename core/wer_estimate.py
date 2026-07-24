"""Lightweight transcript quality telemetry (TDD §17 — WER sampling proxy)."""

from __future__ import annotations

from core.models import Transcript
from core.transcribe_confidence import iter_transcript_words


def estimate_wer_proxy(transcript: Transcript, *, min_prob: float) -> float:
    """
    Proxy for word error rate using low-confidence token share.

    Replaced by human-correction sampling when edit telemetry exists.
    """
    words = [w for w in iter_transcript_words(transcript) if w.text.strip()]
    if not words:
        return 0.0
    low = sum(1 for w in words if w.probability < min_prob)
    return low / len(words)

"""
Deterministic virality fallback when LLM/Ollama is unavailable.

Produces a ViralityResult-compatible score (0–100) from transcript text,
clip duration, and optional audio/chat signal floats. Never calls a network.
"""

from __future__ import annotations

import re

from core.models import Emotion
from core.virality import ViralityResult

HEURISTIC_REASON = "Heuristic virality (LLM unavailable)"

# Short-form sweet spot (seconds): moderate bonus inside, soft penalty outside.
_DURATION_IDEAL_LO = 15.0
_DURATION_IDEAL_HI = 45.0
_DURATION_HARD_LO = 8.0
_DURATION_HARD_HI = 90.0

_HOOK_PHRASES: tuple[str, ...] = (
    "oh my god",
    "oh my gosh",
    "no way",
    "what the",
    "wait what",
    "watch this",
    "look at",
    "check this",
    "you won't believe",
    "are you kidding",
    "i can't believe",
    "lets go",
    "let's go",
    "hold up",
    "bro what",
    "chat look",
    "dude",
    "insane",
    "holy ",
)

_LAUGHTER_WORDS: tuple[str, ...] = (
    "lol",
    "lmao",
    "lmfao",
    "haha",
    "hahaha",
    "hehe",
    "rofl",
    "funny",
    "hilarious",
    "dead",
)

_EMOTION_CUES: tuple[tuple[Emotion, tuple[str, ...]], ...] = (
    (Emotion.HYPE, ("lets go", "let's go", "hype", "insane", "pog", "goated")),
    (Emotion.RAGE, ("rage", "angry", "mad", "wtf", "what the hell")),
    (Emotion.FUNNY, ("lol", "lmao", "haha", "funny", "hilarious", "joke")),
    (Emotion.CLUTCH, ("clutch", "1v", "ace", "nutted", "won that")),
    (Emotion.FAIL, ("fail", "missed", "whiff", "died", "lost")),
    (Emotion.WEIRD, ("weird", "what", "huh", "bro what")),
)

_WORD_RE = re.compile(r"[a-z0-9']+")


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _duration_score(duration: float) -> float:
    """0–1 contribution for short-form length fit."""
    if duration <= 0:
        return 0.0
    if _DURATION_IDEAL_LO <= duration <= _DURATION_IDEAL_HI:
        return 1.0
    if duration < _DURATION_HARD_LO:
        return max(0.0, duration / _DURATION_HARD_LO) * 0.35
    if duration > _DURATION_HARD_HI:
        return max(0.0, 1.0 - (duration - _DURATION_HARD_HI) / 60.0) * 0.35
    if duration < _DURATION_IDEAL_LO:
        span = _DURATION_IDEAL_LO - _DURATION_HARD_LO
        return 0.35 + 0.65 * ((duration - _DURATION_HARD_LO) / max(span, 0.001))
    span = _DURATION_HARD_HI - _DURATION_IDEAL_HI
    return 0.35 + 0.65 * (1.0 - (duration - _DURATION_IDEAL_HI) / max(span, 0.001))


def _hook_hits(lower: str) -> int:
    return sum(1 for phrase in _HOOK_PHRASES if phrase in lower)


def _laughter_hits(words: list[str]) -> int:
    laugh = set(_LAUGHTER_WORDS)
    return sum(1 for w in words if w in laugh)


def _punct_density(text: str, words: list[str]) -> float:
    if not words:
        return 0.0
    marks = text.count("?") + text.count("!")
    return min(1.0, marks / max(len(words) * 0.08, 1.0))


def _infer_emotion(lower: str) -> Emotion:
    best = Emotion.NEUTRAL
    best_hits = 0
    for emotion, cues in _EMOTION_CUES:
        hits = sum(1 for c in cues if c in lower)
        if hits > best_hits:
            best = emotion
            best_hits = hits
    return best


def _meme_keywords(lower: str, *, limit: int = 4) -> list[str]:
    found: list[str] = []
    for phrase in _HOOK_PHRASES + _LAUGHTER_WORDS:
        token = phrase.strip()
        if token and token in lower and token not in found:
            found.append(token)
        if len(found) >= limit:
            break
    return found


def heuristic_virality_score(
    *,
    text: str,
    start_secs: float,
    end_secs: float,
    audio_score: float | None = None,
    chat_score: float | None = None,
) -> ViralityResult:
    """
    Deterministic 0–100 virality estimate from transcript + duration + optional signals.

    Weights (before clamp): base + hooks + punct + laughter + duration + audio + chat.
    """
    duration = max(0.0, end_secs - start_secs)
    raw = (text or "").strip()
    lower = raw.lower()
    words = _WORD_RE.findall(lower)

    hooks = _hook_hits(lower)
    laughter = _laughter_hits(words)
    punct = _punct_density(raw, words)
    dur = _duration_score(duration)

    # Base keeps empty/quiet clips above absolute zero but clearly low.
    score = 18.0
    score += min(28.0, hooks * 9.0)
    score += punct * 16.0
    score += min(18.0, laughter * 6.0)
    score += dur * 22.0

    if audio_score is not None:
        score += _clamp(float(audio_score), 0.0, 1.0) * 12.0
    if chat_score is not None:
        score += _clamp(float(chat_score), 0.0, 1.0) * 10.0

    if not words:
        score *= 0.55

    final = round(_clamp(score), 1)
    emotion = _infer_emotion(lower) if words else Emotion.NEUTRAL
    factors: list[str] = []
    if not words:
        factors.append("no speech")
    else:
        if hooks:
            factors.append(f"hooks×{hooks}")
        if punct >= 0.35:
            factors.append("punctuation")
        if laughter:
            factors.append(f"laughter×{laughter}")
        if dur >= 0.85:
            factors.append("duration fit")
        elif dur <= 0.4:
            factors.append("duration off")
        if audio_score is not None and float(audio_score) >= 0.55:
            factors.append("audio+")
        if chat_score is not None and float(chat_score) >= 0.55:
            factors.append("chat+")
    reason = HEURISTIC_REASON
    if factors:
        reason = f"{HEURISTIC_REASON}: {', '.join(factors[:4])}"
    return ViralityResult(
        score=final,
        emotion=emotion,
        reason=reason,
        meme_keywords=_meme_keywords(lower),
    )

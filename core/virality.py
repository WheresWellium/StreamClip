"""
StreamClip — Post-hoc virality scoring

Virality is a metadata metric computed after clip candidates exist — it never
gates clip creation. Discovery (``core/highlights.py``) ranks segments using
audio, spectral novelty, and optical flow only.
"""

from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

import structlog

from core.config import HighlightConfig, LLMConfig, Settings
from core.content_profiles import ProfileWeights
from core.models import Emotion

log = structlog.get_logger(__name__)

_VIRALITY_PROMPT = """\
You are an expert gaming content strategist who has studied 100,000+ viral clips
across Twitch, TikTok, YouTube Shorts, and Instagram Reels.

Analyse this finished clip transcript and score its viral potential for short-form.

── VIRAL SIGNALS (score high) ────────────────────────────────────────────────
• Kill streaks, clutch plays, emotional outbursts, quotable one-liners
• Unexpected twists, funny fails, hype moments

── ANTI-VIRAL SIGNALS (score low) ────────────────────────────────────────────
• Dead air, filler, menu chatter, mid-explanation without payoff

── CLIP ───────────────────────────────────────────────────────────────────────
Duration: {duration:.1f}s | Window: {start:.1f}s – {end:.1f}s

"{text}"

── OUTPUT FORMAT ──────────────────────────────────────────────────────────────
Return ONLY valid JSON (no markdown fences):
{{
  "score": <integer 0–100>,
  "emotion": "<one of: hype|rage|funny|clutch|fail|weird|neutral>",
  "meme_keywords": ["<keyword1>", "<keyword2>"],
  "reason": "<1–2 sentences explaining the score>"
}}"""


@dataclass(frozen=True)
class ViralityResult:
    score: float
    emotion: Emotion
    reason: str
    meme_keywords: list[str]


def _build_client(cfg: LLMConfig) -> Any:
    if cfg.provider == "ollama":
        from ollama import Client
        return Client(host=cfg.base_url)
    if cfg.provider == "openai":
        from openai import OpenAI
        return OpenAI(api_key=cfg.api_key, base_url=cfg.base_url or None)
    if cfg.provider == "anthropic":
        from anthropic import Anthropic
        return Anthropic(api_key=cfg.api_key)
    raise ValueError(f"Unknown LLM provider: {cfg.provider!r}")


def _call_llm(client: Any, cfg: LLMConfig, prompt: str) -> str:
    if cfg.provider == "ollama":
        resp = client.chat(
            model=cfg.model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": cfg.temperature},
        )
        return resp.message.content.strip()
    if cfg.provider == "anthropic":
        resp = client.messages.create(
            model=cfg.model,
            max_tokens=1024,
            temperature=cfg.temperature,
            messages=[{"role": "user", "content": prompt}],
            timeout=cfg.timeout_secs,
        )
        return resp.content[0].text.strip()
    resp = client.chat.completions.create(
        model=cfg.model,
        messages=[{"role": "user", "content": prompt}],
        temperature=cfg.temperature,
        timeout=cfg.timeout_secs,
    )
    return resp.choices[0].message.content.strip()


def score_clip_virality(
    *,
    text: str,
    start_secs: float,
    end_secs: float,
    cfg: Settings,
    client: Any | None = None,
) -> ViralityResult:
    """Score a finished clip transcript for viral potential (0–100)."""
    duration = max(0.0, end_secs - start_secs)
    prompt = _VIRALITY_PROMPT.format(
        text=text,
        start=start_secs,
        end=end_secs,
        duration=duration,
    )
    llm_client = client or _build_client(cfg.llm)

    for attempt in range(cfg.llm.max_retries):
        try:
            raw = _call_llm(llm_client, cfg.llm, prompt)
            raw = re.sub(r"```[a-z]*\n?", "", raw).strip()
            data = json.loads(raw)
            emotion_str = data.get("emotion", "neutral")
            try:
                emotion = Emotion(emotion_str)
            except ValueError:
                emotion = Emotion.NEUTRAL
            return ViralityResult(
                score=float(data.get("score", 0)),
                emotion=emotion,
                reason=str(data.get("reason", "")),
                meme_keywords=list(data.get("meme_keywords", [])),
            )
        except (json.JSONDecodeError, Exception) as exc:
            log.warning("virality_score_retry", attempt=attempt + 1, error=str(exc))
            time.sleep(1.5 ** attempt)

    return ViralityResult(
        score=0.0,
        emotion=Emotion.NEUTRAL,
        reason="Virality scoring unavailable",
        meme_keywords=[],
    )


def score_clips_virality_parallel(
    clips: list[tuple[str, float, float]],
    cfg: Settings,
    *,
    max_workers: int | None = None,
) -> list[ViralityResult]:
    """
    Score multiple clips concurrently (I/O-bound LLM calls).
    Each item is (transcript_text, start_secs, end_secs).
    """
    if not clips:
        return []
    workers = min(max_workers or cfg.llm.parallel_workers, len(clips))
    client = _build_client(cfg.llm)

    def _score_one(item: tuple[str, float, float]) -> ViralityResult:
        text, start, end = item
        return score_clip_virality(
            text=text,
            start_secs=start,
            end_secs=end,
            cfg=cfg,
            client=client,
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(_score_one, clips))


def ensemble_with_virality(
    *,
    llm_score: float,
    audio_score: float,
    spectral_score: float,
    flow_score: float,
    chat_score: float = 0.0,
    hcfg: HighlightConfig,
    skip_optical_flow: bool = False,
    has_chat: bool = False,
    profile: ProfileWeights | None = None,
) -> float:
    """Combine discovery signals with post-hoc virality into one rank score."""
    llm_norm = llm_score / 100.0
    if profile is not None:
        w_llm = profile.weight_llm_virality
        w_audio = profile.weight_audio_energy
        w_spectral = profile.weight_spectral_novelty
        w_flow = 0.0 if skip_optical_flow else profile.weight_optical_flow
        w_chat = profile.weight_chat_spikes if has_chat else 0.0
    else:
        w_llm = hcfg.weight_llm_virality
        w_audio = hcfg.weight_audio_energy
        w_spectral = hcfg.weight_spectral_novelty
        w_flow = 0.0 if skip_optical_flow else hcfg.weight_optical_flow
        w_chat = hcfg.weight_chat_spikes if has_chat else 0.0
    w_total = w_llm + w_audio + w_spectral + w_flow + w_chat
    if w_total <= 0:
        w_total = 1.0
    return (
        w_llm * llm_norm
        + w_audio * audio_score
        + w_spectral * spectral_score
        + w_flow * flow_score
        + w_chat * chat_score
    ) / w_total

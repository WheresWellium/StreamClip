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

from core.chat_spikes import ChatEvent
from core.config import HighlightConfig, LLMConfig, Settings
from core.content_profiles import ProfileWeights
from core.models import Emotion

log = structlog.get_logger(__name__)


# ─── Per-profile prompt personas ──────────────────────────────────────────────

@dataclass(frozen=True)
class _ProfilePrompt:
    persona: str
    viral: str
    anti_viral: str


_PROFILE_PROMPTS: dict[str, _ProfilePrompt] = {
    "gaming": _ProfilePrompt(
        persona="an expert gaming content strategist who has studied 100,000+ viral "
                "clips across Twitch, TikTok, YouTube Shorts, and Instagram Reels",
        viral="• Kill streaks, clutch plays, emotional outbursts, quotable one-liners\n"
              "• Unexpected twists, funny fails, hype moments, streamer rage or disbelief",
        anti_viral="• Dead air, filler, menu chatter, mid-explanation without payoff",
    ),
    "esports": _ProfilePrompt(
        persona="a veteran esports broadcast producer who clips tournament moments "
                "that trend on X and TikTok within hours",
        viral="• Match-point clutches, upsets, caster scream moments, crowd eruptions\n"
              "• Player mechanics that make even non-fans say 'how?'",
        anti_viral="• Standard trades, pause chatter, analysis without a payoff moment",
    ),
    "irl": _ProfilePrompt(
        persona="an IRL/just-chatting clip curator who knows what makes strangers "
                "stop scrolling on unscripted real-life content",
        viral="• Unexpected encounters, genuine emotional reactions, awkward-but-funny "
              "social moments\n• Quotable hot takes, wholesome surprises, chaos in public",
        anti_viral="• Walking with no dialogue, logistics talk, waiting around",
    ),
    "podcast": _ProfilePrompt(
        persona="a podcast growth editor who cuts long conversations into shorts that "
                "consistently break 1M views",
        viral="• Contrarian or surprising claims, vulnerable personal stories, heated "
              "disagreements\n• Tight self-contained insights with a hook in the first "
              "sentence, punchy comebacks",
        anti_viral="• Mid-thought rambling, inside references without setup, "
              "pleasantries and sponsor reads",
    ),
    "education": _ProfilePrompt(
        persona="an educational shorts editor who turns lessons into 'today I learned' "
                "clips people share",
        viral="• Counterintuitive facts, myth-busting, 'nobody tells you this' framing\n"
              "• A complete micro-lesson: question, answer, and why it matters",
        anti_viral="• Prerequisite-heavy fragments, housekeeping, incomplete explanations",
    ),
    "vlog": _ProfilePrompt(
        persona="a lifestyle content editor who clips vlogs into shorts with strong "
                "narrative hooks",
        viral="• Reveals and transformations, candid confessions, relatable struggles\n"
              "• Moments with a clear beginning-middle-punchline arc",
        anti_viral="• Routine narration without stakes, transitions, filler updates",
    ),
    "sports": _ProfilePrompt(
        persona="a sports highlights producer who knows which plays go viral beyond "
                "the fanbase",
        viral="• Game-winning or impossible plays, records broken, huge hits or saves\n"
              "• Raw emotion: celebrations, benches clearing, commentator losing it",
        anti_viral="• Routine plays, stoppage time, tactical talk without a visual payoff",
    ),
    "music": _ProfilePrompt(
        persona="a music content editor who clips performances and studio moments that "
                "trend on TikTok and Reels",
        viral="• The drop, the high note, the crowd singing back, improvised magic\n"
              "• Artist reactions, first-take wow moments, unexpected covers",
        anti_viral="• Tuning, soundcheck, talking over the music without a moment",
    ),
    "general": _ProfilePrompt(
        persona="a short-form video strategist who has studied viral clips across "
                "every content vertical on TikTok, YouTube Shorts, and Instagram Reels",
        viral="• Strong hooks in the first 2 seconds, emotional peaks, quotable lines\n"
              "• Surprises, payoffs, and moments that provoke comments or shares",
        anti_viral="• Dead air, filler, context-dependent fragments without payoff",
    ),
}


@dataclass(frozen=True)
class ClipScoringContext:
    """Optional evidence given to the LLM alongside the clip transcript."""
    content_profile: str = "general"
    audio_score: float | None = None
    spectral_score: float | None = None
    flow_score: float | None = None
    chat_score: float | None = None
    chat_excerpts: tuple[str, ...] = ()
    text_before: str = ""
    text_after: str = ""


def select_chat_excerpts(
    events: list[ChatEvent],
    start: float,
    end: float,
    *,
    limit: int = 12,
    max_chars: int = 80,
) -> tuple[str, ...]:
    """Pick up to ``limit`` chat messages inside the clip window for LLM context."""
    window = [e for e in events if start <= e.offset_secs <= end and e.text.strip()]
    if len(window) > limit:
        # Even sampling across the window preserves the reaction arc
        step = len(window) / limit
        window = [window[int(i * step)] for i in range(limit)]
    return tuple(e.text.strip()[:max_chars] for e in window)


def build_virality_prompt(
    *,
    text: str,
    start: float,
    end: float,
    duration: float,
    context: ClipScoringContext | None = None,
) -> str:
    """Assemble the scoring prompt: profile persona + clip + optional evidence."""
    ctx = context or ClipScoringContext()
    pp = _PROFILE_PROMPTS.get(ctx.content_profile, _PROFILE_PROMPTS["general"])

    sections: list[str] = [
        f"You are {pp.persona}.",
        "",
        "Analyse this finished clip and score its viral potential for short-form.",
        "",
        "── VIRAL SIGNALS (score high) ────────────────────────────────────────────────",
        pp.viral,
        "",
        "── ANTI-VIRAL SIGNALS (score low) ────────────────────────────────────────────",
        pp.anti_viral,
        "",
        "── CLIP ───────────────────────────────────────────────────────────────────────",
        f"Duration: {duration:.1f}s | Window: {start:.1f}s – {end:.1f}s",
        "",
        f'"{text}"',
    ]

    signals = [
        ("Audio energy", ctx.audio_score),
        ("Spectral novelty", ctx.spectral_score),
        ("Visual motion", ctx.flow_score),
        ("Chat spike", ctx.chat_score),
    ]
    known = [(name, v) for name, v in signals if v is not None]
    if known:
        sections += [
            "",
            "── SIGNAL TELEMETRY (0–1, measured from the video) ───────────────────────────",
            " | ".join(f"{name}: {v:.2f}" for name, v in known),
            "Use these to corroborate or challenge your read of the transcript — "
            "high audio/chat with flat text often means a non-verbal hype moment.",
        ]

    if ctx.chat_excerpts:
        joined = "\n".join(f"• {m}" for m in ctx.chat_excerpts)
        sections += [
            "",
            "── LIVE CHAT DURING CLIP ─────────────────────────────────────────────────────",
            joined,
        ]

    if ctx.text_before or ctx.text_after:
        sections += [
            "",
            "── SURROUNDING TRANSCRIPT (context only — do not score this) ─────────────────",
        ]
        if ctx.text_before:
            sections.append(f"Before: \"{ctx.text_before}\"")
        if ctx.text_after:
            sections.append(f"After: \"{ctx.text_after}\"")

    sections += [
        "",
        "── OUTPUT FORMAT ──────────────────────────────────────────────────────────────",
        "Return ONLY valid JSON (no markdown fences):",
        "{",
        '  "score": <integer 0–100>,',
        '  "emotion": "<one of: hype|rage|funny|clutch|fail|weird|neutral>",',
        '  "meme_keywords": ["<keyword1>", "<keyword2>"],',
        '  "reason": "<1–2 sentences explaining the score>"',
        "}",
    ]
    return "\n".join(sections)


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
            format="json",
            options={"temperature": cfg.temperature, "num_predict": cfg.num_predict},
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
    context: ClipScoringContext | None = None,
) -> ViralityResult:
    """Score a finished clip transcript for viral potential (0–100)."""
    duration = max(0.0, end_secs - start_secs)
    prompt = build_virality_prompt(
        text=text,
        start=start_secs,
        end=end_secs,
        duration=duration,
        context=context,
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
    contexts: list[ClipScoringContext | None] | None = None,
) -> list[ViralityResult]:
    """
    Score multiple clips concurrently (I/O-bound LLM calls).
    Each item is (transcript_text, start_secs, end_secs); ``contexts`` is an
    optional list aligned 1:1 with ``clips``.
    """
    if not clips:
        return []
    if contexts is not None and len(contexts) != len(clips):
        raise ValueError("contexts must align 1:1 with clips")
    workers = min(max_workers or cfg.llm.parallel_workers, len(clips))
    client = _build_client(cfg.llm)

    def _score_one(idx_item: tuple[int, tuple[str, float, float]]) -> ViralityResult:
        idx, (text, start, end) = idx_item
        return score_clip_virality(
            text=text,
            start_secs=start,
            end_secs=end,
            cfg=cfg,
            client=client,
            context=contexts[idx] if contexts else None,
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(_score_one, enumerate(clips)))


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

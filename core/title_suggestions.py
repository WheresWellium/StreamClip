"""
LLM-backed title suggestions for completed jobs.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

import structlog

from core.clip_metadata import derive_clip_metadata
from core.config import Settings
from core.creator_options import is_valid_content_profile
from core.virality import _build_client, _call_llm

log = structlog.get_logger(__name__)

DEFAULT_TONE = "gaming"

VALID_TONES = frozenset({"gaming", "tutorial", "tip", "explainer", "promo"})

TONE_PERSONAS: dict[str, str] = {
    "gaming": "hype streamer writing Shorts titles",
    "tutorial": "patient educator writing how-to Shorts titles",
    "tip": "creator sharing quick actionable Shorts tips",
    "explainer": "curiosity-driven Shorts explainer",
    "promo": "high-energy promo Shorts copywriter",
}

TITLE_PROMPT_TEMPLATE = """\
You are a {persona}. Given a clip transcript and job metadata, produce exactly
three ranked title suggestions for a {content_profile} clip.

── JOB METADATA ───────────────────────────────────────────────────────────────
{job_metadata}

── TRANSCRIPT ─────────────────────────────────────────────────────────────────
{transcript_text}

── OUTPUT FORMAT ──────────────────────────────────────────────────────────────
Return ONLY valid JSON (no markdown fences):
{{
  "suggestions": [
    {{"rank": 1, "title": "<string ≤ 80 chars>", "hook": "<one-line payoff>", "confidence": 0.91, "tone": "{tone}"}},
    {{"rank": 2, "title": "<string ≤ 80 chars>", "hook": "<one-line payoff>", "confidence": 0.84, "tone": "{tone}"}},
    {{"rank": 3, "title": "<string ≤ 80 chars>", "hook": "<one-line payoff>", "confidence": 0.78, "tone": "{tone}"}}
  ]
}}
Return exactly 3 suggestions, ranked by confidence descending. Titles must not
repeat the raw transcript opening verbatim — write scroll-stopping hooks.
"""


@dataclass(frozen=True)
class TitleSuggestion:
    rank: int
    title: str
    hook: str
    confidence: float
    tone: str


def _format_job_metadata(metadata: dict[str, Any]) -> str:
    lines = [f"{key}: {value}" for key, value in metadata.items() if value]
    return "\n".join(lines) if lines else "(none)"


def _fallback_suggestions(transcript_text: str, tone: str) -> list[TitleSuggestion]:
    title, hook = derive_clip_metadata(transcript_text[:500] if transcript_text else "")
    base_title = title if title != "Untitled clip" else "Highlight reel moment"
    base_hook = hook or "Watch the full clip."
    return [
        TitleSuggestion(rank=1, title=base_title, hook=base_hook, confidence=0.55, tone=tone),
        TitleSuggestion(
            rank=2,
            title=f"{base_title} — best moment",
            hook=base_hook,
            confidence=0.45,
            tone=tone,
        ),
        TitleSuggestion(
            rank=3,
            title="You need to see this",
            hook=base_hook,
            confidence=0.35,
            tone=tone,
        ),
    ]


def _parse_suggestions(data: dict[str, Any], tone: str) -> list[TitleSuggestion]:
    raw = data.get("suggestions", [])
    if not isinstance(raw, list):
        raise ValueError("suggestions must be a list")
    out: list[TitleSuggestion] = []
    for item in raw[:3]:
        out.append(
            TitleSuggestion(
                rank=int(item.get("rank", len(out) + 1)),
                title=str(item.get("title", "")).strip()[:80],
                hook=str(item.get("hook", "")).strip()[:180],
                confidence=float(item.get("confidence", 0.5)),
                tone=str(item.get("tone", tone)),
            ),
        )
    if len(out) < 3:
        raise ValueError("expected 3 suggestions")
    return out


def generate_title_suggestions(
    transcript_text: str,
    job_metadata: dict[str, Any],
    cfg: Settings,
    *,
    tone: str = DEFAULT_TONE,
) -> list[TitleSuggestion]:
    """Return ranked title suggestions for a job transcript."""
    normalized_tone = tone if tone in VALID_TONES else DEFAULT_TONE
    profile = str(job_metadata.get("content_profile", "gaming"))
    if not is_valid_content_profile(profile):
        profile = "gaming"
    persona = TONE_PERSONAS[normalized_tone]
    prompt = TITLE_PROMPT_TEMPLATE.format(
        persona=persona,
        content_profile=profile.replace("_", " "),
        job_metadata=_format_job_metadata(job_metadata),
        transcript_text=transcript_text[:4000] or "(empty transcript)",
        tone=normalized_tone,
    )
    llm_client = _build_client(cfg.llm)

    for attempt in range(cfg.llm.max_retries):
        try:
            raw = _call_llm(llm_client, cfg.llm, prompt)
            raw = re.sub(r"```[a-z]*\n?", "", raw).strip()
            data = json.loads(raw)
            return _parse_suggestions(data, normalized_tone)
        except (json.JSONDecodeError, ValueError, TypeError, KeyError, Exception) as exc:
            log.warning("title_suggestions_retry", attempt=attempt + 1, error=str(exc))
            time.sleep(1.5 ** attempt)

    return _fallback_suggestions(transcript_text, normalized_tone)

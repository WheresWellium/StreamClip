"""Classify sources into processing tiers for cost-aware pipeline routing."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from core.ingest.types import ProcessingTier, SourceKind

# Twitch clip URL patterns
_TWITCH_CLIP = re.compile(
    r"(clips\.twitch\.tv/|twitch\.tv/[^/]+/clip/|/clip/)",
    re.I,
)
_SHORT_HOSTS = ("youtube.com/shorts/", "youtu.be/", "tiktok.com/")


def classify_url(url: str) -> ProcessingTier:
    """Heuristic tier from URL shape (before download)."""
    lower = url.lower()
    if _TWITCH_CLIP.search(lower):
        return ProcessingTier.SHORT
    if any(h in lower for h in _SHORT_HOSTS):
        return ProcessingTier.SHORT
    return ProcessingTier.LONG


def classify_duration(duration_secs: float) -> ProcessingTier:
    """Refine tier after ffprobe."""
    if duration_secs <= 120:
        return ProcessingTier.SHORT
    if duration_secs <= 600:
        return ProcessingTier.MEDIUM
    return ProcessingTier.LONG


def resolve_tier(
    *,
    source_kind: SourceKind,
    url: str | None = None,
    duration_secs: float | None = None,
) -> ProcessingTier:
    """Combine URL heuristics with probed duration."""
    tier = ProcessingTier.MEDIUM
    if source_kind == SourceKind.URL and url:
        tier = classify_url(url)
    if duration_secs is not None:
        duration_tier = classify_duration(duration_secs)
        # Use the cheaper (shorter) tier when both signals agree directionally
        order = (ProcessingTier.SHORT, ProcessingTier.MEDIUM, ProcessingTier.LONG)
        tier = order[min(order.index(tier), order.index(duration_tier))]
    return tier

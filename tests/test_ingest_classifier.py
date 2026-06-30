"""Processing tier classification tests."""

from __future__ import annotations

from core.ingest.classifier import (
    classify_duration,
    classify_url,
    resolve_tier,
)
from core.ingest.types import ProcessingTier, SourceKind


def test_twitch_clip_url_is_short_tier():
    url = "https://clips.twitch.tv/FancyClip-abc123"
    assert classify_url(url) == ProcessingTier.SHORT


def test_youtube_shorts_url_is_short_tier():
    assert classify_url("https://youtube.com/shorts/abc") == ProcessingTier.SHORT


def test_vod_url_defaults_long():
    assert classify_url("https://www.twitch.tv/videos/123456") == ProcessingTier.LONG


def test_classify_duration_buckets():
    assert classify_duration(60) == ProcessingTier.SHORT
    assert classify_duration(300) == ProcessingTier.MEDIUM
    assert classify_duration(3600) == ProcessingTier.LONG


def test_resolve_tier_picks_cheaper_when_duration_confirms_short():
    tier = resolve_tier(
        source_kind=SourceKind.URL,
        url="https://www.twitch.tv/videos/999",
        duration_secs=45,
    )
    assert tier == ProcessingTier.SHORT


def test_upload_uses_duration_only():
    tier = resolve_tier(
        source_kind=SourceKind.UPLOAD,
        duration_secs=90,
    )
    assert tier == ProcessingTier.SHORT

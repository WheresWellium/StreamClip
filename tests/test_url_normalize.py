"""Source URL normalization tests."""

from __future__ import annotations

import pytest

from core.ingest.url_normalize import normalize_source_url


def test_twitch_vod_with_www():
    url = normalize_source_url("www.twitch.tv/videos/123456")
    assert url == "https://twitch.tv/videos/123456"


def test_twitch_vod_strips_query():
    url = normalize_source_url("https://www.twitch.tv/videos/123456?filter=archives&sort=time")
    assert url == "https://www.twitch.tv/videos/123456"


def test_twitch_clip_url():
    url = normalize_source_url("https://clips.twitch.tv/FancyClip-abc123")
    assert url == "https://clips.twitch.tv/FancyClip-abc123"


def test_twitch_channel_clip():
    url = normalize_source_url("https://www.twitch.tv/streamer/clip/SlugName")
    assert url == "https://www.twitch.tv/streamer/clip/SlugName"


def test_mobile_twitch_host():
    url = normalize_source_url("https://m.twitch.tv/videos/999")
    assert url == "https://www.twitch.tv/videos/999"


def test_bare_twitch_vod_gets_https():
    url = normalize_source_url("twitch.tv/videos/42")
    assert url == "https://twitch.tv/videos/42"


def test_empty_raises():
    with pytest.raises(ValueError, match="empty"):
        normalize_source_url("   ")


def test_unknown_host_without_scheme_raises():
    with pytest.raises(ValueError, match="http"):
        normalize_source_url("example.com/video.mp4")

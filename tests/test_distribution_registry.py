"""Platform registry and adapter factory."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from core.config import get_settings
from core.distribution.credentials import OAuthAppCredentials
from core.distribution.registry import build_adapter, get_adapter, get_platform_meta, list_platforms
from core.distribution.tiktok import TikTokAdapter
from core.distribution.youtube import YouTubeShortsAdapter
from core.errors import StreamClipError

APP = OAuthAppCredentials(client_id="c", client_secret="s", redirect_uri="http://cb")


def test_get_platform_meta():
    meta = get_platform_meta("youtube_shorts")
    assert meta is not None
    assert meta.id == "youtube_shorts"
    assert get_platform_meta("unknown") is None


def test_get_adapter_youtube_and_tiktok():
    assert isinstance(get_adapter("youtube_shorts", APP), YouTubeShortsAdapter)
    assert isinstance(get_adapter("tiktok", APP), TikTokAdapter)


def test_get_adapter_unknown():
    with pytest.raises(StreamClipError):
        get_adapter("myspace", APP)


def test_list_platforms_respects_flags(monkeypatch):
    cfg = get_settings(reload=True)
    cfg.distribution.youtube_publish_enabled = True
    cfg.distribution.tiktok_publish_enabled = False
    ids = {p.id for p in list_platforms()}
    assert "youtube_shorts" in ids
    assert "tiktok" not in ids


@pytest.mark.asyncio
async def test_build_adapter_delegates():
    db = AsyncMock()
    with patch(
        "core.distribution.credentials.resolve_oauth_app",
        AsyncMock(return_value=APP),
    ):
        adapter = await build_adapter(db, "youtube_shorts")
    assert isinstance(adapter, YouTubeShortsAdapter)

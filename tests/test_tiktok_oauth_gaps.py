"""TikTok adapter OAuth and multi-chunk upload paths."""

from __future__ import annotations

import json

import httpx
import pytest

import core.distribution.tiktok as tiktok_mod
from core.distribution.credentials import OAuthAppCredentials
from core.distribution.tiktok import TikTokAdapter

APP = OAuthAppCredentials(client_id="ck", client_secret="cs", redirect_uri="http://cb")


def _patch_transport(monkeypatch, handler) -> None:
    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    class PatchedClient(real_client):
        def __init__(self, **kw):
            kw.pop("transport", None)
            super().__init__(transport=transport, **kw)

    monkeypatch.setattr(tiktok_mod.httpx, "AsyncClient", PatchedClient)


@pytest.mark.asyncio
async def test_get_auth_url():
    url = await TikTokAdapter(APP).get_auth_url("http://cb", state="st")
    assert "client_key=ck" in url
    assert "state=st" in url


@pytest.mark.asyncio
async def test_exchange_code(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "open.tiktokapis.com"
        return httpx.Response(200, json={
            "access_token": "at",
            "refresh_token": "rt",
            "expires_in": 3600,
            "open_id": "oid",
        })

    _patch_transport(monkeypatch, handler)
    creds = await TikTokAdapter(APP).exchange_code("code", "http://cb")
    assert creds.access_token == "at"
    assert creds.refresh_token == "rt"


@pytest.mark.asyncio
async def test_refresh_token_keeps_old_refresh(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "access_token": "new-at",
            "expires_in": 3600,
        })

    _patch_transport(monkeypatch, handler)
    creds = await TikTokAdapter(APP).refresh_token("old-rt")
    assert creds.access_token == "new-at"
    assert creds.refresh_token == "old-rt"


@pytest.mark.asyncio
async def test_fetch_user_label_fallback(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401)

    _patch_transport(monkeypatch, handler)
    label = await TikTokAdapter(APP).fetch_user_label("tok")
    assert label == "TikTok"


@pytest.mark.asyncio
async def test_fetch_user_label_display_name(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"user": {"display_name": "Creator"}}})

    _patch_transport(monkeypatch, handler)
    label = await TikTokAdapter(APP).fetch_user_label("tok")
    assert label == "Creator"


@pytest.mark.asyncio
async def test_publish_stub():
    from core.distribution.base import PublishMetadata, PlatformCredentials

    result = await TikTokAdapter(APP).publish(
        "key",
        PublishMetadata(title="t", description="d", tags=[]),
        PlatformCredentials(
            platform_id="tiktok",
            access_token="at",
            refresh_token="rt",
            expires_at=None,
        ),
    )
    assert result.status == "pending"


@pytest.mark.asyncio
async def test_upload_multi_chunk(monkeypatch, tmp_path):
    from core.distribution.base import PublishMetadata
    from core.distribution.tiktok import TIKTOK_INBOX_INIT_URL, TIKTOK_STATUS_URL

    video = tmp_path / "big.mp4"
    video.write_bytes(b"\x00" * (5 * 1024 * 1024 + 100))

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == TIKTOK_INBOX_INIT_URL:
            return httpx.Response(200, json={
                "data": {"publish_id": "p1", "upload_url": "https://up.example/chunk"},
                "error": {"code": "ok"},
            })
        if "up.example" in url:
            return httpx.Response(201)
        if url == TIKTOK_STATUS_URL:
            return httpx.Response(200, json={
                "data": {"status": "SEND_TO_USER_INBOX"},
                "error": {"code": "ok"},
            })
        raise AssertionError(url)

    _patch_transport(monkeypatch, handler)
    meta = PublishMetadata(title="T", description="d", tags=[])
    result = await TikTokAdapter(APP).upload_video_file(video, meta, "tok")
    assert result.status == "published"

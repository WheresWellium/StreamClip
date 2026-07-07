"""YouTube Shorts adapter against mocked Google APIs."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

import core.distribution.youtube as yt_mod
from core.distribution.base import PlatformCredentials, PublishMetadata
from core.distribution.credentials import OAuthAppCredentials
from core.distribution.youtube import (
    GOOGLE_TOKEN_URL,
    YOUTUBE_UPLOAD_URL,
    YouTubeShortsAdapter,
)
from core.errors import StreamClipError

APP = OAuthAppCredentials(client_id="gid", client_secret="gsec", redirect_uri="http://cb")
META = PublishMetadata(title="My Short", description="desc", tags=[])
UPLOAD_SESSION = "https://upload.googleapis.com/upload/youtube/v3/videos?upload_id=abc"


def _patch_transport(monkeypatch, handler) -> None:
    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    class PatchedClient(real_client):
        def __init__(self, **kw):
            kw.pop("transport", None)
            super().__init__(transport=transport, **kw)

    monkeypatch.setattr(yt_mod.httpx, "AsyncClient", PatchedClient)


@pytest.fixture
def video(tmp_path):
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"\x00" * 4096)
    return path


async def test_get_auth_url():
    url = await YouTubeShortsAdapter(APP).get_auth_url("http://cb", state="st")
    assert "accounts.google.com" in url
    assert "client_id=gid" in url
    assert "state=st" in url


async def test_exchange_code_and_refresh(monkeypatch):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.host or "")
        if request.url == GOOGLE_TOKEN_URL:
            if b"authorization_code" in request.content:
                return httpx.Response(200, json={
                    "access_token": "at1",
                    "refresh_token": "rt1",
                    "expires_in": 3600,
                })
            return httpx.Response(200, json={"access_token": "at2", "expires_in": 1800})
        raise AssertionError(request.url)

    _patch_transport(monkeypatch, handler)
    adapter = YouTubeShortsAdapter(APP)
    creds = await adapter.exchange_code("code", "http://cb")
    assert creds.access_token == "at1"
    assert creds.refresh_token == "rt1"
    assert creds.expires_at is not None

    refreshed = await adapter.refresh_token("rt1")
    assert refreshed.access_token == "at2"
    assert refreshed.refresh_token == "rt1"


async def test_token_exchange_failure(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="bad code")

    _patch_transport(monkeypatch, handler)
    with pytest.raises(StreamClipError) as exc:
        await YouTubeShortsAdapter(APP).exchange_code("bad", "http://cb")
    assert exc.value.code == "oauth_exchange_failed"


async def test_fetch_channel_label_success(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "items": [{"snippet": {"title": "Creator Channel"}}],
        })

    _patch_transport(monkeypatch, handler)
    label = await YouTubeShortsAdapter(APP).fetch_channel_label("tok")
    assert label == "Creator Channel"


async def test_fetch_channel_label_fallbacks(monkeypatch):
    def fail_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403)

    _patch_transport(monkeypatch, fail_handler)
    assert await YouTubeShortsAdapter(APP).fetch_channel_label("tok") == "YouTube"

    def empty_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": []})

    _patch_transport(monkeypatch, empty_handler)
    assert await YouTubeShortsAdapter(APP).fetch_channel_label("tok") == "YouTube"


async def test_upload_happy_path(monkeypatch, video):
    progress: list[tuple[str, float]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and str(request.url).startswith(YOUTUBE_UPLOAD_URL):
            return httpx.Response(200, headers={"Location": UPLOAD_SESSION})
        if request.method == "PUT":
            assert len(request.content) == 4096
            return httpx.Response(200, json={"id": "vid123"})
        raise AssertionError(f"{request.method} {request.url}")

    _patch_transport(monkeypatch, handler)
    result = await YouTubeShortsAdapter(APP).upload_video_file(
        video,
        META,
        "tok",
        on_progress=lambda s, p: progress.append((s, p)),
    )
    assert result.status == "published"
    assert "shorts/vid123" in result.external_url
    assert progress


async def test_upload_missing_file(tmp_path):
    result = await YouTubeShortsAdapter(APP).upload_video_file(
        tmp_path / "missing.mp4",
        META,
        "tok",
    )
    assert result.status == "failed"


async def test_upload_init_rejected(monkeypatch, video):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="quota exceeded")

    _patch_transport(monkeypatch, handler)
    result = await YouTubeShortsAdapter(APP).upload_video_file(video, META, "tok")
    assert result.status == "failed"
    assert "quota" in result.message


async def test_upload_no_location_header(monkeypatch, video):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={})

    _patch_transport(monkeypatch, handler)
    result = await YouTubeShortsAdapter(APP).upload_video_file(video, META, "tok")
    assert "upload URL" in result.message


async def test_upload_put_failure(monkeypatch, video):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, headers={"Location": UPLOAD_SESSION})
        return httpx.Response(500, text="boom")

    _patch_transport(monkeypatch, handler)
    result = await YouTubeShortsAdapter(APP).upload_video_file(video, META, "tok")
    assert result.status == "failed"
    assert "upload failed" in result.message.lower()


async def test_upload_missing_video_id(monkeypatch, video):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, headers={"Location": UPLOAD_SESSION})
        return httpx.Response(200, json={})

    _patch_transport(monkeypatch, handler)
    result = await YouTubeShortsAdapter(APP).upload_video_file(video, META, "tok")
    assert "video id" in result.message.lower()


async def test_publish_schedule_revoke(monkeypatch):
    revoked: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if "oauth2.googleapis.com/revoke" in str(request.url):
            revoked.append(request.url.params.get("token", ""))
        return httpx.Response(200)

    _patch_transport(monkeypatch, handler)
    adapter = YouTubeShortsAdapter(APP)
    creds = PlatformCredentials(
        platform_id="youtube_shorts",
        access_token="tok",
        refresh_token="rt",
        expires_at=datetime.now(timezone.utc),
    )
    pub = await adapter.publish("key", META, creds)
    assert pub.status == "pending"
    when = datetime(2026, 1, 1, tzinfo=timezone.utc)
    sched = await adapter.schedule("key", META, creds, when)
    assert sched.status == "scheduled"
    await adapter.revoke(creds)
    assert revoked == ["tok"]

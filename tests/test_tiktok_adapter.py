"""TikTok inbox-upload adapter against a mocked Content Posting API."""

from __future__ import annotations

import json

import httpx
import pytest

import core.distribution.tiktok as tiktok_mod
from core.distribution.base import PublishMetadata
from core.distribution.credentials import OAuthAppCredentials
from core.distribution.tiktok import (
    TIKTOK_INBOX_INIT_URL,
    TIKTOK_STATUS_URL,
    TikTokAdapter,
)

APP = OAuthAppCredentials(client_id="ck", client_secret="cs", redirect_uri="http://cb")
META = PublishMetadata(title="Clip", description="desc", tags=[])
UPLOAD_URL = "https://upload.tiktokapis.example/upload/42"


def _patch_transport(monkeypatch, handler) -> None:
    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    class PatchedClient(real_client):
        def __init__(self, **kw):
            kw.pop("transport", None)
            super().__init__(transport=transport, **kw)

    monkeypatch.setattr(tiktok_mod.httpx, "AsyncClient", PatchedClient)


@pytest.fixture
def video(tmp_path):
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"\x00" * 2048)
    return path


async def test_upload_happy_path_lands_in_inbox(monkeypatch, video):
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == TIKTOK_INBOX_INIT_URL:
            seen["init"] = json.loads(request.content)
            return httpx.Response(200, json={
                "data": {"publish_id": "pub123", "upload_url": UPLOAD_URL},
                "error": {"code": "ok"},
            })
        if url == UPLOAD_URL:
            seen["range"] = request.headers.get("Content-Range")
            seen["bytes"] = len(request.content)
            return httpx.Response(201)
        if url == TIKTOK_STATUS_URL:
            return httpx.Response(200, json={
                "data": {"status": "SEND_TO_USER_INBOX"},
                "error": {"code": "ok"},
            })
        raise AssertionError(f"unexpected url {url}")

    _patch_transport(monkeypatch, handler)
    progress: list[tuple[str, float]] = []
    result = await TikTokAdapter(APP).upload_video_file(
        video, META, "tok", on_progress=lambda s, p: progress.append((s, p)),
    )

    assert result.status == "published"
    assert "inbox" in result.message.lower()
    init = seen["init"]["source_info"]
    assert init["video_size"] == 2048
    assert init["total_chunk_count"] == 1
    assert seen["range"] == "bytes 0-2047/2048"
    assert seen["bytes"] == 2048
    assert progress[-1][0] == "finalize"


async def test_upload_init_rejected(monkeypatch, video):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={
            "error": {"code": "invalid_param", "message": "bad chunk size"},
        })

    _patch_transport(monkeypatch, handler)
    result = await TikTokAdapter(APP).upload_video_file(video, META, "tok")
    assert result.status == "failed"
    assert "bad chunk size" in result.message


async def test_upload_put_failure(monkeypatch, video):
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == TIKTOK_INBOX_INIT_URL:
            return httpx.Response(200, json={
                "data": {"publish_id": "pub123", "upload_url": UPLOAD_URL},
                "error": {"code": "ok"},
            })
        return httpx.Response(500, text="storage exploded")

    _patch_transport(monkeypatch, handler)
    result = await TikTokAdapter(APP).upload_video_file(video, META, "tok")
    assert result.status == "failed"
    assert "upload failed" in result.message.lower()


async def test_processing_failure_reported(monkeypatch, video):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == TIKTOK_INBOX_INIT_URL:
            return httpx.Response(200, json={
                "data": {"publish_id": "pub123", "upload_url": UPLOAD_URL},
                "error": {"code": "ok"},
            })
        if url == UPLOAD_URL:
            return httpx.Response(201)
        return httpx.Response(200, json={
            "data": {"status": "FAILED", "fail_reason": "video_too_long"},
        })

    _patch_transport(monkeypatch, handler)
    result = await TikTokAdapter(APP).upload_video_file(video, META, "tok")
    assert result.status == "failed"
    assert "video_too_long" in result.message


async def test_missing_file_fails_fast(tmp_path):
    result = await TikTokAdapter(APP).upload_video_file(
        tmp_path / "nope.mp4", META, "tok",
    )
    assert result.status == "failed"

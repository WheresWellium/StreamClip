"""Upload presigned URL endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.api.schemas import UploadInitResponse
from backend.middleware.scope import RequestScope, get_request_scope


@pytest.fixture
def uploads_client(app, client):
    scope = RequestScope(user_id=None, device_id="uploaddev00001")
    app.dependency_overrides[get_request_scope] = lambda: scope
    yield client
    app.dependency_overrides.pop(get_request_scope, None)


@pytest.mark.asyncio
async def test_init_upload(uploads_client, monkeypatch):
    expected = UploadInitResponse(
        upload_id="up-1",
        storage_key="uploads/x.mp4",
        upload_url="https://minio/upload",
        expires_in=3600,
    )

    class FakeUploadService:
        def __init__(self, cfg, storage) -> None:
            pass

        async def init_upload(self, body, scope):
            return expected

    monkeypatch.setattr("backend.api.uploads.UploadService", FakeUploadService)
    resp = await uploads_client.post(
        "/api/uploads/init",
        json={"filename": "clip.mp4", "content_type": "video/mp4"},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_get_download_url(uploads_client, monkeypatch):
    storage = MagicMock()
    storage.presigned_get_url.return_value = "https://minio/get/key"

    with patch("backend.api.uploads.make_storage", return_value=storage):
        resp = await uploads_client.get("/api/uploads/url", params={"key": "clips/x.mp4"})

    assert resp.status_code == 200
    assert resp.json()["url"] == "https://minio/get/key"

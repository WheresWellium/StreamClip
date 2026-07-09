"""HTTP tests for local storage GET/PUT (ADR-001 §4.3)."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import create_app
from core.config import get_settings


@pytest.fixture
def local_storage_env(tmp_path, monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.storage, "backend", "local")
    monkeypatch.setattr(cfg.storage, "local_root", tmp_path)
    monkeypatch.setattr(cfg.storage, "public_base_url", "")
    return cfg, tmp_path


@pytest.mark.asyncio
async def test_local_storage_put_and_get(local_storage_env):
    _cfg, root = local_storage_env
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        put = await client.put(
            "/storage/uploads/test/video.mp4?upload=1",
            content=b"fake-mp4-bytes",
        )
        assert put.status_code == 200

        get = await client.get("/storage/uploads/test/video.mp4")
        assert get.status_code == 200
        assert get.content == b"fake-mp4-bytes"
        assert "video/mp4" in get.headers.get("content-type", "")

    assert (root / "uploads" / "test" / "video.mp4").exists()


@pytest.mark.asyncio
async def test_local_storage_get_missing(local_storage_env):
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/storage/missing/file.bin")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_local_storage_put_requires_upload_query(local_storage_env):
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.put("/storage/x.bin", content=b"x")
        assert resp.status_code == 405


@pytest.mark.asyncio
async def test_local_storage_image_content_types(local_storage_env):
    _cfg, root = local_storage_env
    app = create_app()
    transport = ASGITransport(app=app)
    cases = [
        ("shot.jpg", b"jpeg", "image/jpeg"),
        ("shot.png", b"png", "image/png"),
        ("shot.webp", b"webp", "image/webp"),
    ]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for name, payload, media in cases:
            key = f"uploads/test/{name}"
            put = await client.put(f"/storage/{key}?upload=1", content=payload)
            assert put.status_code == 200
            get = await client.get(f"/storage/{key}")
            assert get.status_code == 200
            assert media in get.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_local_storage_put_oserror(local_storage_env, monkeypatch):
    app = create_app()
    transport = ASGITransport(app=app)

    def boom(self, data):  # noqa: ANN001
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_bytes", boom)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.put("/storage/uploads/fail.bin?upload=1", content=b"x")
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_local_storage_unavailable_when_not_local(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.storage, "backend", "minio")
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/storage/jobs/x/clips/a.mp4")
        assert resp.status_code == 404

"""Publish task retry paths, terminal failure, storage resolution, beat task."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from core.distribution.base import PublishResult
from core.distribution.youtube import YouTubeShortsAdapter
from core.errors import StorageError
from core.tasks import publish_tasks as pt


def _asyncio_run(coro):
    return asyncio.run(coro)


@pytest.fixture
def mock_db_cm():
    session = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    with patch.object(pt, "db_session", return_value=cm):
        yield session


@pytest.fixture(autouse=True)
def patch_safe_async():
    with patch.object(pt, "_safe_async", side_effect=_asyncio_run):
        yield


def _job(**overrides):
    base = dict(
        id="pj-1",
        platform="youtube_shorts",
        connection_id="conn-1",
        clip_id="clip-1",
        vault_clip_id=None,
        title="T",
        description="D",
        status="pending",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _happy_mocks(mock_db_cm, *, download_error=None):
    job = _job()
    repo = MagicMock()
    repo.claim_for_publish = AsyncMock(return_value=job)
    repo.mark_failed = AsyncMock()
    repo.release_claim = AsyncMock(return_value=job)
    repo.get = AsyncMock(return_value=job)
    repo.mark_published = AsyncMock()

    storage = MagicMock()
    storage.exists.return_value = True
    if download_error:
        storage.download.side_effect = download_error
    else:
        storage.download.side_effect = lambda key, dest, on_progress=None: dest.write_bytes(b"x")

    mock_db_cm.get = AsyncMock(
        side_effect=lambda model, pk: SimpleNamespace(final_storage_key="clips/f.mp4")
        if pk == "clip-1"
        else SimpleNamespace(id="conn-1"),
    )
    return job, repo, storage


def test_publish_transient_error_releases_claim(mock_db_cm):
    _, repo, storage = _happy_mocks(
        mock_db_cm,
        download_error=httpx.TransportError("timeout"),
    )

    pt.publish_to_platform.push_request(retries=0)
    try:
        with patch.object(pt, "make_storage", return_value=storage), \
             patch.object(pt, "PublishJobRepository", return_value=repo), \
             patch.object(pt, "ensure_fresh_credentials", new=AsyncMock(return_value=SimpleNamespace(access_token="tok"))), \
             patch.object(pt, "publish_job_progress"), \
             patch.object(pt, "record_publish_outcome"):
            with pytest.raises(httpx.TransportError):
                pt.publish_to_platform.run("pj-1")
    finally:
        pt.publish_to_platform.pop_request()
    repo.release_claim.assert_awaited()


def test_publish_transient_error_terminal(mock_db_cm):
    _, repo, storage = _happy_mocks(
        mock_db_cm,
        download_error=StorageError("disk full"),
    )

    pt.publish_to_platform.push_request(retries=3)
    try:
        with patch.object(pt, "make_storage", return_value=storage), \
             patch.object(pt, "PublishJobRepository", return_value=repo), \
             patch.object(pt, "ensure_fresh_credentials", new=AsyncMock(return_value=SimpleNamespace(access_token="tok"))), \
             patch.object(pt, "publish_job_progress"), \
             patch.object(pt, "notify_publish_event", new=AsyncMock()), \
             patch.object(pt, "record_publish_outcome"):
            with pytest.raises(StorageError):
                pt.publish_to_platform.run("pj-1")
    finally:
        pt.publish_to_platform.pop_request()
    repo.mark_failed.assert_awaited()


def test_publish_upload_progress_callback(mock_db_cm):
    _, repo, storage = _happy_mocks(mock_db_cm)
    adapter = MagicMock(spec=YouTubeShortsAdapter)
    adapter.upload_video_file = AsyncMock(
        return_value=PublishResult(status="published", message="ok", external_url="https://yt/1"),
    )

    with patch.object(pt, "make_storage", return_value=storage), \
         patch.object(pt, "PublishJobRepository", return_value=repo), \
         patch.object(pt, "ensure_fresh_credentials", new=AsyncMock(return_value=SimpleNamespace(access_token="tok"))), \
         patch.object(pt, "build_adapter", new=AsyncMock(return_value=adapter)), \
         patch.object(pt, "publish_job_progress") as prog, \
         patch.object(pt, "notify_publish_event", new=AsyncMock()), \
         patch.object(pt, "record_publish_outcome"):
        out = pt.publish_to_platform.run("pj-1")

    assert out["status"] == "published"
    upload_calls = [c for c in adapter.upload_video_file.await_args_list]
    assert upload_calls
    on_progress = upload_calls[0].kwargs.get("on_progress")
    assert on_progress is not None
    on_progress("upload", 0.5)
    assert prog.called


def test_mark_failed_terminal(mock_db_cm):
    repo = MagicMock()
    repo.mark_failed = AsyncMock()
    repo.get = AsyncMock(return_value=SimpleNamespace(platform="youtube_shorts", id="pj-1"))
    with patch.object(pt, "PublishJobRepository", return_value=repo), \
         patch.object(pt, "notify_publish_event", new=AsyncMock()), \
         patch.object(pt, "record_publish_outcome"), \
         patch.object(pt, "publish_job_progress"):
        pt._mark_failed_terminal("pj-1", RuntimeError("boom"), 0.0)
    repo.mark_failed.assert_awaited()


@pytest.mark.asyncio
async def test_resolve_storage_key_paths(mock_db_cm):
    clip = SimpleNamespace(final_storage_key="clips/f.mp4")
    vault = SimpleNamespace(storage_key="vault/v.mp4")
    mock_db_cm.get = AsyncMock(
        side_effect=lambda model, pk: clip if pk == "clip-1" else vault if pk == "vault-1" else None,
    )

    assert await pt._resolve_storage_key(mock_db_cm, SimpleNamespace(clip_id="clip-1", vault_clip_id=None)) == "clips/f.mp4"
    assert await pt._resolve_storage_key(mock_db_cm, SimpleNamespace(clip_id=None, vault_clip_id="vault-1")) == "vault/v.mp4"
    assert await pt._resolve_storage_key(mock_db_cm, SimpleNamespace(clip_id="missing", vault_clip_id=None)) is None
    assert await pt._resolve_storage_key(mock_db_cm, SimpleNamespace(clip_id=None, vault_clip_id=None)) is None


def test_process_due_scheduled_jobs(mock_db_cm):
    repo = MagicMock()
    repo.list_due_scheduled = AsyncMock(return_value=[SimpleNamespace(id="pj-due")])
    repo.promote_scheduled_to_pending = AsyncMock(return_value=SimpleNamespace(id="pj-due"))

    with patch.object(pt, "PublishJobRepository", return_value=repo), \
         patch.object(pt.publish_to_platform, "delay") as delay:
        out = pt.process_due_scheduled_jobs.run()
    assert out["enqueued"] == ["pj-due"]
    delay.assert_called_once_with("pj-due")

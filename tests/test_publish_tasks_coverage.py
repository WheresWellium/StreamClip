"""Coverage for core.tasks.publish_tasks — claim, upload, retry, scheduled beat."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.distribution.base import PublishResult
from core.distribution.tiktok import TikTokAdapter
from core.distribution.youtube import YouTubeShortsAdapter
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


@pytest.mark.asyncio
async def test_resolve_storage_key_from_clip(mock_db_cm):
    mock_db_cm.get = AsyncMock(
        side_effect=lambda model, pk: SimpleNamespace(final_storage_key="clips/x.mp4")
        if pk == "clip-1"
        else None,
    )
    key = await pt._resolve_storage_key(mock_db_cm, _job())
    assert key == "clips/x.mp4"


@pytest.mark.asyncio
async def test_resolve_storage_key_from_vault(mock_db_cm):
    job = _job(clip_id=None, vault_clip_id="vc-1")
    mock_db_cm.get = AsyncMock(
        side_effect=lambda model, pk: SimpleNamespace(storage_key="vault/x.mp4")
        if pk == "vc-1"
        else None,
    )
    key = await pt._resolve_storage_key(mock_db_cm, job)
    assert key == "vault/x.mp4"


def test_publish_skipped_when_not_claimable(mock_db_cm):
    repo = MagicMock()
    repo.claim_for_publish = AsyncMock(return_value=None)
    repo.get = AsyncMock(return_value=_job(status="pending"))

    with patch.object(pt, "make_storage", return_value=MagicMock()), \
         patch.object(pt, "PublishJobRepository", return_value=repo):
        out = pt.publish_to_platform.run("pj-1")

    assert out["status"] == "skipped"


def test_publish_already_published(mock_db_cm):
    repo = MagicMock()
    repo.claim_for_publish = AsyncMock(return_value=None)
    repo.get = AsyncMock(return_value=_job(status="published"))

    with patch.object(pt, "make_storage", return_value=MagicMock()), \
         patch.object(pt, "PublishJobRepository", return_value=repo):
        out = pt.publish_to_platform.run("pj-1")

    assert out["status"] == "published"


def test_publish_fails_when_storage_missing(mock_db_cm):
    job = _job()
    repo = MagicMock()
    repo.claim_for_publish = AsyncMock(return_value=job)
    repo.mark_failed = AsyncMock()
    repo.get = AsyncMock(return_value=job)

    storage = MagicMock()
    storage.exists.return_value = False

    mock_db_cm.get = AsyncMock(return_value=SimpleNamespace(final_storage_key=None))

    with patch.object(pt, "make_storage", return_value=storage), \
         patch.object(pt, "PublishJobRepository", return_value=repo), \
         patch.object(pt, "publish_job_progress"), \
         patch.object(pt, "notify_publish_event", new=AsyncMock()), \
         patch.object(pt, "record_publish_outcome"):
        out = pt.publish_to_platform.run("pj-1")

    assert out["status"] == "failed"
    repo.mark_failed.assert_awaited()


def test_publish_success_youtube(mock_db_cm, tmp_path):
    job = _job()
    connection = SimpleNamespace(id="conn-1")
    clip = SimpleNamespace(final_storage_key="clips/f.mp4")

    repo = MagicMock()
    repo.claim_for_publish = AsyncMock(return_value=job)
    repo.mark_published = AsyncMock()
    repo.get = AsyncMock(return_value=job)

    storage = MagicMock()
    storage.exists.return_value = True

    def _download(key, dest, on_progress=None):
        dest.write_bytes(b"mp4")

    storage.download.side_effect = _download

    mock_db_cm.get = AsyncMock(
        side_effect=lambda model, pk: clip if pk == "clip-1" else connection,
    )

    adapter = MagicMock(spec=YouTubeShortsAdapter)
    adapter.upload_video_file = AsyncMock(
        return_value=PublishResult(
            status="published",
            external_url="https://youtube.com/shorts/abc123",
            message="ok",
        ),
    )

    with patch.object(pt, "make_storage", return_value=storage), \
         patch.object(pt, "PublishJobRepository", return_value=repo), \
         patch.object(pt, "ensure_fresh_credentials", new=AsyncMock(return_value=SimpleNamespace(access_token="tok"))), \
         patch.object(pt, "build_adapter", new=AsyncMock(return_value=adapter)), \
         patch.object(pt, "publish_job_progress"), \
         patch.object(pt, "notify_publish_event", new=AsyncMock()), \
         patch.object(pt, "record_publish_outcome"):
        out = pt.publish_to_platform.run("pj-1")

    assert out["status"] == "published"
    assert "youtube.com" in out["external_url"]
    repo.mark_published.assert_awaited()


def test_publish_success_tiktok(mock_db_cm, tmp_path):
    job = _job(platform="tiktok")
    connection = SimpleNamespace(id="conn-1")
    clip = SimpleNamespace(final_storage_key="clips/f.mp4")

    repo = MagicMock()
    repo.claim_for_publish = AsyncMock(return_value=job)
    repo.mark_published = AsyncMock()
    repo.get = AsyncMock(return_value=job)

    storage = MagicMock()
    storage.exists.return_value = True
    storage.download.side_effect = lambda key, dest, on_progress=None: dest.write_bytes(b"mp4")

    mock_db_cm.get = AsyncMock(
        side_effect=lambda model, pk: clip if pk == "clip-1" else connection,
    )

    adapter = MagicMock(spec=TikTokAdapter)
    adapter.upload_video_file = AsyncMock(
        return_value=PublishResult(
            status="published",
            external_url="https://tiktok.com/@u/video/123",
            message="ok",
        ),
    )

    with patch.object(pt, "make_storage", return_value=storage), \
         patch.object(pt, "PublishJobRepository", return_value=repo), \
         patch.object(pt, "ensure_fresh_credentials", new=AsyncMock(return_value=SimpleNamespace(access_token="tok"))), \
         patch.object(pt, "build_adapter", new=AsyncMock(return_value=adapter)), \
         patch.object(pt, "publish_job_progress"), \
         patch.object(pt, "notify_publish_event", new=AsyncMock()), \
         patch.object(pt, "record_publish_outcome"):
        out = pt.publish_to_platform.run("pj-1")

    assert out["status"] == "published"
    assert "tiktok.com" in out["external_url"]
    repo.mark_published.assert_awaited()


def test_process_due_scheduled_jobs(mock_db_cm):
    due_job = _job(status="scheduled")
    repo = MagicMock()
    repo.list_due_scheduled = AsyncMock(return_value=[due_job])
    repo.promote_scheduled_to_pending = AsyncMock(return_value=due_job)

    with patch.object(pt, "PublishJobRepository", return_value=repo), \
         patch.object(pt, "publish_to_platform") as task:
        task.delay = MagicMock()
        out = pt.process_due_scheduled_jobs.run()

    assert out["enqueued"] == ["pj-1"]
    task.delay.assert_called_once_with("pj-1")


def test_mark_failed_terminal(mock_db_cm):
    job = _job()
    repo = MagicMock()
    repo.mark_failed = AsyncMock()
    repo.get = AsyncMock(return_value=job)

    with patch.object(pt, "PublishJobRepository", return_value=repo), \
         patch.object(pt, "notify_publish_event", new=AsyncMock()), \
         patch.object(pt, "record_publish_outcome"), \
         patch.object(pt, "publish_job_progress"):
        pt._mark_failed_terminal("pj-1", RuntimeError("boom"), started_at=0.0)

    repo.mark_failed.assert_awaited()


def test_publish_fails_on_unknown_adapter(mock_db_cm):
    job = _job(platform="myspace")
    connection = SimpleNamespace(id="conn-1")
    clip = SimpleNamespace(final_storage_key="clips/f.mp4")

    repo = MagicMock()
    repo.claim_for_publish = AsyncMock(return_value=job)
    repo.mark_failed = AsyncMock()
    repo.get = AsyncMock(return_value=job)

    storage = MagicMock()
    storage.exists.return_value = True
    storage.download.side_effect = lambda key, dest, on_progress=None: dest.write_bytes(b"x")

    mock_db_cm.get = AsyncMock(
        side_effect=lambda model, pk: clip if pk == "clip-1" else connection,
    )

    unknown = MagicMock()
    unknown.__class__.__name__ = "MyspaceAdapter"

    with patch.object(pt, "make_storage", return_value=storage), \
         patch.object(pt, "PublishJobRepository", return_value=repo), \
         patch.object(pt, "ensure_fresh_credentials", new=AsyncMock(return_value=SimpleNamespace(access_token="tok"))), \
         patch.object(pt, "build_adapter", new=AsyncMock(return_value=unknown)), \
         patch.object(pt, "publish_job_progress"), \
         patch.object(pt, "notify_publish_event", new=AsyncMock()), \
         patch.object(pt, "record_publish_outcome"):
        out = pt.publish_to_platform.run("pj-1")

    assert out["status"] == "failed"
    repo.mark_failed.assert_awaited()


def test_publish_platform_rejected(mock_db_cm):
    job = _job()
    connection = SimpleNamespace(id="conn-1")
    clip = SimpleNamespace(final_storage_key="clips/f.mp4")

    repo = MagicMock()
    repo.claim_for_publish = AsyncMock(return_value=job)
    repo.mark_failed = AsyncMock()
    repo.get = AsyncMock(return_value=job)

    storage = MagicMock()
    storage.exists.return_value = True
    storage.download.side_effect = lambda key, dest, on_progress=None: dest.write_bytes(b"x")

    mock_db_cm.get = AsyncMock(
        side_effect=lambda model, pk: clip if pk == "clip-1" else connection,
    )

    adapter = MagicMock(spec=YouTubeShortsAdapter)
    adapter.upload_video_file = AsyncMock(
        return_value=PublishResult(status="failed", message="rejected", external_url=None),
    )

    with patch.object(pt, "make_storage", return_value=storage), \
         patch.object(pt, "PublishJobRepository", return_value=repo), \
         patch.object(pt, "ensure_fresh_credentials", new=AsyncMock(return_value=SimpleNamespace(access_token="tok"))), \
         patch.object(pt, "build_adapter", new=AsyncMock(return_value=adapter)), \
         patch.object(pt, "publish_job_progress"), \
         patch.object(pt, "notify_publish_event", new=AsyncMock()), \
         patch.object(pt, "record_publish_outcome"):
        out = pt.publish_to_platform.run("pj-1")

    assert out["status"] == "failed"


def test_publish_fails_without_connection(mock_db_cm):
    job = _job()
    repo = MagicMock()
    repo.claim_for_publish = AsyncMock(return_value=job)
    repo.mark_failed = AsyncMock()
    repo.get = AsyncMock(return_value=job)

    storage = MagicMock()
    storage.exists.return_value = True
    storage.download.side_effect = lambda key, dest, on_progress=None: dest.write_bytes(b"x")

    mock_db_cm.get = AsyncMock(
        side_effect=lambda model, pk: SimpleNamespace(final_storage_key="clips/f.mp4")
        if pk == "clip-1"
        else None,
    )

    with patch.object(pt, "make_storage", return_value=storage), \
         patch.object(pt, "PublishJobRepository", return_value=repo), \
         patch.object(pt, "publish_job_progress"), \
         patch.object(pt, "notify_publish_event", new=AsyncMock()), \
         patch.object(pt, "record_publish_outcome"):
        out = pt.publish_to_platform.run("pj-1")

    assert out["status"] == "failed"
    repo.mark_failed.assert_awaited()


def test_report_helper():
    with patch.object(pt, "publish_job_progress") as prog:
        pt._report("pj-1", "upload", 0.5, "halfway")
    prog.assert_called_once()

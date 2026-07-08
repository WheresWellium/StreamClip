"""Close remaining §3.7 hot-path line gaps (pipeline_tasks, sse, publish_tasks, distribution)."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery.exceptions import Retry

import backend.api.distribution as distribution_api
from backend.db.session import get_db
from backend.middleware.auth import get_current_user_id, require_user_id
from backend.middleware.distribution import require_distribution_access
from backend.services import sse as sse_mod
from backend.services.sse import stream_job_progress, stream_publish_progress
from core.config import get_settings
from core.distribution.tiktok import TikTokAdapter
from core.errors import StreamClipError
from core.progress_bus import get_progress_bus, reset_progress_bus
from core.tasks import pipeline_tasks as pt
from core.tasks import publish_tasks as pub_pt

USER_ID = "oauth-user-1"


class FakeSession:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


@pytest.fixture
def dist_client(app, client):
    session = FakeSession()

    async def fake_db():
        yield session

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[require_distribution_access] = lambda: USER_ID
    app.dependency_overrides[require_user_id] = lambda: USER_ID
    app.dependency_overrides[get_current_user_id] = lambda: USER_ID
    yield SimpleNamespace(client=client, session=session, app=app)
    for dep in (get_db, require_distribution_access, require_user_id, get_current_user_id):
        app.dependency_overrides.pop(dep, None)


def _publish_row(**overrides) -> SimpleNamespace:
    base = dict(
        id="pj-1",
        clip_id="clip-1",
        vault_clip_id=None,
        platform="youtube_shorts",
        status="pending",
        scheduled_at=None,
        published_at=None,
        external_id=None,
        external_url=None,
        title="T",
        description="D",
        error_message=None,
        last_error_code=None,
        created_at=datetime.now(timezone.utc),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _asyncio_run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _patch_pt_safe_async():
    with patch.object(pt, "_safe_async", side_effect=_asyncio_run):
        yield


@pytest.fixture(autouse=True)
def _patch_pub_safe_async():
    with patch.object(pub_pt, "_safe_async", side_effect=_asyncio_run):
        yield


@pytest.fixture
def mock_db_cm():
    session = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    with patch.object(pt, "db_session", return_value=cm), patch.object(pub_pt, "db_session", return_value=cm):
        yield session


# ─── pipeline_tasks ──────────────────────────────────────────────────────────


def test_safe_async_run_until_complete_when_loop_idle():
    async def coro():
        return 42

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        assert pt._safe_async(coro()) == 42
    finally:
        loop.close()
        asyncio.set_event_loop(asyncio.new_event_loop())


def test_run_transcribe_job_not_found(mock_db_cm):
    with patch.object(pt, "JobRepository") as JR, patch.object(pt, "_mark_error"):
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=None)
        JR.return_value = jobs
        with pytest.raises(StreamClipError, match="not found"):
            pt.run_transcribe.run("missing-job")


def test_run_transcribe_streamclip_error_marks_failed(mock_db_cm):
    job = SimpleNamespace(
        id="job-t",
        source_url=None,
        source_storage_key="uploads/x.mp4",
        config_snapshot={},
    )
    with patch.object(pt, "JobRepository") as JR, \
         patch.object(pt, "_ensure_job_source", side_effect=StreamClipError("bad source")):
        jobs = MagicMock()
        jobs.get = AsyncMock(return_value=job)
        jobs.update_status = AsyncMock()
        JR.return_value = jobs
        with patch.object(pt, "_mark_error") as mark:
            with pytest.raises(StreamClipError):
                pt.run_transcribe.run("job-t")
            mark.assert_called_once()


def test_process_clip_missing_entities(mock_db_cm):
    with patch.object(pt, "ClipRepository") as CR, \
         patch.object(pt, "JobRepository") as JR, \
         patch.object(pt, "_mark_clip_error", new_callable=AsyncMock) as mark_err:
        CR.return_value.get = AsyncMock(return_value=None)
        JR.return_value.get = AsyncMock(return_value=None)
        pt.process_clip.run("job-x", "clip-x")
        mark_err.assert_awaited()


def test_publish_unexpected_exception_marks_terminal(mock_db_cm):
    job = SimpleNamespace(
        id="pj-1",
        platform="youtube_shorts",
        connection_id="conn-1",
        clip_id="clip-1",
        vault_clip_id=None,
        title="T",
        description="D",
        status="pending",
    )
    repo = MagicMock()
    repo.claim_for_publish = AsyncMock(return_value=job)
    repo.get = AsyncMock(return_value=job)
    repo.mark_failed = AsyncMock()

    storage = MagicMock()
    storage.exists.return_value = True
    storage.download.side_effect = RuntimeError("boom")

    mock_db_cm.get = AsyncMock(
        side_effect=lambda model, pk: SimpleNamespace(final_storage_key="clips/f.mp4")
        if pk == "clip-1"
        else SimpleNamespace(id="conn-1"),
    )

    with patch.object(pub_pt, "make_storage", return_value=storage), \
         patch.object(pub_pt, "PublishJobRepository", return_value=repo), \
         patch.object(pub_pt, "ensure_fresh_credentials", new=AsyncMock(return_value=SimpleNamespace(access_token="tok"))), \
         patch.object(pub_pt, "publish_job_progress"), \
         patch.object(pub_pt, "notify_publish_event", new=AsyncMock()), \
         patch.object(pub_pt, "record_publish_outcome"), \
         patch.object(pub_pt, "_mark_failed_terminal") as mark:
        with pytest.raises(RuntimeError):
            pub_pt.publish_to_platform.run("pj-1")
        mark.assert_called_once()


# ─── SSE in-process + redis ───────────────────────────────────────────────────


@pytest.fixture
def inprocess_cfg(monkeypatch):
    cfg = get_settings(reload=True)
    monkeypatch.setattr(cfg.queue, "backend", "inprocess")
    return cfg


@pytest.fixture(autouse=True)
def _fresh_bus():
    reset_progress_bus()
    yield
    reset_progress_bus()


@pytest.mark.asyncio
async def test_stream_publish_inprocess_live_invalid_json(inprocess_cfg):
    cfg = inprocess_cfg
    bus = get_progress_bus(cfg)
    channel = f"{cfg.redis.publish_pubsub_channel_prefix}pj-mem-bad"
    queue = bus.subscribe(channel)

    async def publish_raw():
        await asyncio.sleep(0.05)
        queue.put_nowait("plain-text")
        bus.publish(channel, {"status": "done", "stage": "done", "progress": 1.0})

    task = asyncio.create_task(publish_raw())
    try:
        chunks = [c async for c in stream_publish_progress("pj-mem-bad", cfg, heartbeat_secs=100)]
    finally:
        await task
    assert any("done" in c for c in chunks)


@pytest.mark.asyncio
async def test_stream_publish_inprocess_heartbeat(inprocess_cfg):
    cfg = inprocess_cfg
    gen = stream_publish_progress("pj-hb", cfg, heartbeat_secs=0.0)
    await gen.__anext__()
    second = await gen.__anext__()
    assert "heartbeat" in second
    await gen.aclose()


@pytest.mark.asyncio
async def test_stream_job_redis_heartbeat_zero():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)

    async def get_message(**_kwargs):
        await asyncio.sleep(0)
        return None

    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = get_message
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.close = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_job_progress("job-hb0", cfg, heartbeat_secs=0.0)
        await gen.__anext__()
        hb = await gen.__anext__()
        assert "heartbeat" in hb
        await gen.aclose()


@pytest.mark.asyncio
async def test_stream_publish_redis_cleanup_warning():
    cfg = get_settings()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)
    mock_pubsub.unsubscribe = AsyncMock(side_effect=RuntimeError("cleanup"))
    mock_pubsub.close = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch.object(sse_mod, "get_redis", AsyncMock(return_value=mock_redis)):
        gen = stream_publish_progress("pj-cln", cfg, heartbeat_secs=100)
        await gen.__anext__()
        await gen.aclose()


# ─── distribution API (oauth + progress) ─────────────────────────────────────


@pytest.mark.asyncio
async def test_oauth_start_tiktok(dist_client, monkeypatch):
    adapter = MagicMock(spec=TikTokAdapter)
    adapter.get_auth_url = AsyncMock(return_value="https://tiktok/oauth")

    monkeypatch.setattr(distribution_api, "build_adapter", AsyncMock(return_value=adapter))
    monkeypatch.setattr(distribution_api, "create_oauth_state", lambda *_a, **_k: "state")
    monkeypatch.setattr(distribution_api, "default_redirect_uri", lambda *_a, **_k: "http://cb")
    resp = await dist_client.client.get("/api/distribution/oauth/tiktok/start")
    assert resp.status_code == 200
    assert "tiktok" in resp.json()["auth_url"]


@pytest.mark.asyncio
async def test_oauth_callback_tiktok_success(dist_client, monkeypatch):
    from core.distribution.base import PlatformCredentials

    adapter = MagicMock(spec=TikTokAdapter)
    adapter.exchange_code = AsyncMock(
        return_value=PlatformCredentials(
            platform_id="tiktok",
            access_token="tok",
            refresh_token="ref",
            expires_at=None,
        ),
    )
    adapter.fetch_user_label = AsyncMock(return_value="@user")

    monkeypatch.setattr(distribution_api, "verify_oauth_state", lambda *_a, **_k: USER_ID)
    monkeypatch.setattr(distribution_api, "build_adapter", AsyncMock(return_value=adapter))
    monkeypatch.setattr(distribution_api, "default_redirect_uri", lambda *_a, **_k: "http://cb")
    monkeypatch.setattr(distribution_api, "save_platform_connection", AsyncMock())

    resp = await dist_client.client.get(
        "/api/distribution/oauth/tiktok/callback",
        params={"code": "abc", "state": "st"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 307)
    assert "connected=tiktok" in resp.headers["location"]


@pytest.mark.asyncio
async def test_oauth_callback_streamclip_error(dist_client, monkeypatch):
    monkeypatch.setattr(
        distribution_api,
        "verify_oauth_state",
        MagicMock(side_effect=StreamClipError("bad state")),
    )
    resp = await dist_client.client.get(
        "/api/distribution/oauth/youtube_shorts/callback",
        params={"code": "abc", "state": "st"},
        follow_redirects=False,
    )
    assert "error=oauth_failed" in resp.headers["location"]


@pytest.mark.asyncio
async def test_cancel_publish_not_found(dist_client, monkeypatch):
    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def get_for_user(self, publish_job_id, user_id):
            return None

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    resp = await dist_client.client.post("/api/distribution/publish-jobs/missing/cancel")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_publish_progress_not_found(dist_client, monkeypatch):
    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def get_for_user(self, publish_job_id, user_id):
            return None

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    resp = await dist_client.client.get("/api/distribution/publish-jobs/missing/progress")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_publish_progress_invalid_last_event_id(dist_client, monkeypatch):
    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def get_for_user(self, publish_job_id, user_id):
            return _publish_row()

    async def fake_stream(job_id, cfg, last_event_id=None):
        assert last_event_id is None
        yield 'event: progress\ndata: {"status":"processing"}\n\n'

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    monkeypatch.setattr(distribution_api, "stream_publish_progress", fake_stream)
    resp = await dist_client.client.get(
        "/api/distribution/publish-jobs/pj-1/progress",
        headers={"Last-Event-Id": "not-a-number"},
    )
    assert resp.status_code == 200

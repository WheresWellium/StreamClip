"""HTTP coverage for distribution OAuth, connections, schedule, and edit paths."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import backend.api.distribution as distribution_api
from backend.db.models import UserTier
from backend.db.session import get_db
from backend.middleware.auth import get_current_user_id, require_user_id
from backend.middleware.distribution import require_distribution_access
from core.distribution.base import PlatformCredentials
from core.distribution.credentials import OAuthAppCredentials
from core.distribution.youtube import YouTubeShortsAdapter
from core.distribution.tokens import generate_token_key

USER_ID = "oauth-user-1"
OAUTH_APP = OAuthAppCredentials(client_id="cid", client_secret="sec", redirect_uri="http://cb")


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


@pytest.mark.asyncio
async def test_platforms_marks_connected_platforms(dist_client, monkeypatch):
    conn = SimpleNamespace(platform="youtube_shorts")

    class FakeConnRepo:
        def __init__(self, db) -> None:
            pass

        async def list_for_user(self, user_id):
            return [conn]

    monkeypatch.setattr(distribution_api, "PlatformConnectionRepository", FakeConnRepo)
    resp = await dist_client.client.get("/api/distribution/platforms")
    assert resp.status_code == 200
    yt = next(p for p in resp.json() if p["id"] == "youtube_shorts")
    assert yt["connected"] is True


@pytest.mark.asyncio
async def test_list_oauth_apps(dist_client, monkeypatch):
    row = SimpleNamespace(
        client_id="cid",
        client_secret_enc="enc",
        redirect_uri="http://cb",
    )

    class FakeOAuthRepo:
        def __init__(self, db) -> None:
            pass

        async def get(self, platform):
            return row if platform == "youtube_shorts" else None

    monkeypatch.setattr(distribution_api, "InstallOAuthAppRepository", FakeOAuthRepo)
    resp = await dist_client.client.get("/api/distribution/oauth-apps")
    assert resp.status_code == 200
    apps = {a["platform"]: a for a in resp.json()}
    assert apps["youtube_shorts"]["configured"] is True
    assert apps["tiktok"]["configured"] is False


@pytest.mark.asyncio
async def test_update_oauth_app_requires_encryption_key(dist_client, monkeypatch):
    monkeypatch.setattr(distribution_api, "is_token_key_configured", lambda: False)
    resp = await dist_client.client.put(
        "/api/distribution/oauth-apps/youtube_shorts",
        json={"client_id": "abcd", "client_secret": "secret"},
    )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_update_oauth_app_success(dist_client, monkeypatch, token_key):
    row = SimpleNamespace(client_id="cid", redirect_uri="http://cb", client_secret_enc="x")

    class FakeOAuthRepo:
        def __init__(self, db) -> None:
            pass

        async def upsert(self, **kwargs):
            return row

    monkeypatch.setattr(distribution_api, "InstallOAuthAppRepository", FakeOAuthRepo)
    monkeypatch.setattr(distribution_api, "is_token_key_configured", lambda: True)
    resp = await dist_client.client.put(
        "/api/distribution/oauth-apps/youtube_shorts",
        json={"client_id": "abcd", "client_secret": "secret"},
    )
    assert resp.status_code == 200
    assert resp.json()["configured"] is True
    assert dist_client.session.committed


@pytest.fixture
def token_key(monkeypatch):
    from core.config import get_settings

    key = generate_token_key()
    cfg = get_settings(reload=True)
    old = cfg.distribution.token_encryption_key
    cfg.distribution.token_encryption_key = key
    yield key
    cfg.distribution.token_encryption_key = old


@pytest.mark.asyncio
async def test_oauth_start_youtube(dist_client, monkeypatch):
    adapter = YouTubeShortsAdapter(OAUTH_APP)

    with patch.object(distribution_api, "build_adapter", AsyncMock(return_value=adapter)), \
         patch.object(distribution_api, "create_oauth_state", return_value="state-token"):
        resp = await dist_client.client.get("/api/distribution/oauth/youtube_shorts/start")

    assert resp.status_code == 200
    assert "accounts.google.com" in resp.json()["auth_url"]


@pytest.mark.asyncio
async def test_oauth_callback_success(dist_client, monkeypatch):
    cfg = distribution_api.get_settings()
    web = cfg.distribution.web_origin.rstrip("/")
    creds = PlatformCredentials(
        platform_id="youtube_shorts",
        access_token="at",
        refresh_token="rt",
    )
    adapter = YouTubeShortsAdapter(OAUTH_APP)

    with patch.object(distribution_api, "verify_oauth_state", return_value=USER_ID), \
         patch.object(distribution_api, "build_adapter", AsyncMock(return_value=adapter)), \
         patch.object(distribution_api, "save_platform_connection", AsyncMock()) as save, \
         patch.object(adapter, "exchange_code", AsyncMock(return_value=creds)), \
         patch.object(adapter, "fetch_channel_label", AsyncMock(return_value="My Channel")):
        resp = await dist_client.client.get(
            "/api/distribution/oauth/youtube_shorts/callback",
            params={"code": "auth-code", "state": "st"},
            follow_redirects=False,
        )

    assert resp.status_code == 307
    assert resp.headers["location"] == f"{web}/distribution?connected=youtube_shorts"
    save.assert_awaited()
    assert dist_client.session.committed


@pytest.mark.asyncio
async def test_oauth_callback_denied(dist_client):
    cfg = distribution_api.get_settings()
    web = cfg.distribution.web_origin.rstrip("/")
    resp = await dist_client.client.get(
        "/api/distribution/oauth/youtube_shorts/callback",
        params={"error": "access_denied"},
        follow_redirects=False,
    )
    assert resp.status_code == 307
    assert "oauth_denied" in resp.headers["location"]


@pytest.mark.asyncio
async def test_oauth_callback_failure_redirect(dist_client, monkeypatch):
    cfg = distribution_api.get_settings()
    web = cfg.distribution.web_origin.rstrip("/")

    with patch.object(distribution_api, "verify_oauth_state", side_effect=Exception("bad")):
        resp = await dist_client.client.get(
            "/api/distribution/oauth/youtube_shorts/callback",
            params={"code": "x", "state": "y"},
            follow_redirects=False,
        )

    assert resp.status_code == 307
    assert resp.headers["location"] == f"{web}/distribution?error=oauth_failed"


@pytest.mark.asyncio
async def test_list_and_disconnect_connections(dist_client, monkeypatch):
    conn = SimpleNamespace(
        id="conn-1",
        platform="youtube_shorts",
        account_label="Channel",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        is_active=True,
    )

    class FakeConnRepo:
        def __init__(self, db) -> None:
            pass

        async def list_for_user(self, user_id):
            return [conn]

        async def deactivate(self, connection_id, user_id):
            return conn if connection_id == "conn-1" else None

    monkeypatch.setattr(distribution_api, "PlatformConnectionRepository", FakeConnRepo)
    listed = await dist_client.client.get("/api/distribution/connections")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == "conn-1"

    deleted = await dist_client.client.delete("/api/distribution/connections/conn-1")
    assert deleted.status_code == 204
    assert dist_client.session.committed

    missing = await dist_client.client.delete("/api/distribution/connections/ghost")
    assert missing.status_code == 500


@pytest.mark.asyncio
async def test_schedule_publish(dist_client, monkeypatch):
    when = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)

    class FakeService:
        def __init__(self, db, cfg) -> None:
            pass

        async def publish_now(self, **kwargs):
            assert kwargs["scheduled_at"] == when
            return _publish_row(status="scheduled", scheduled_at=when)

    monkeypatch.setattr(distribution_api, "DistributionService", FakeService)
    resp = await dist_client.client.post(
        "/api/distribution/schedule",
        json={
            "clip_id": "clip-1",
            "platform": "youtube_shorts",
            "scheduled_at": when.isoformat(),
        },
    )
    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_cancel_publish_success(dist_client, monkeypatch):
    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def get_for_user(self, publish_job_id, user_id):
            return _publish_row(status="pending")

        async def cancel(self, publish_job_id):
            return _publish_row(status="cancelled")

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    monkeypatch.setattr(distribution_api, "notify_publish_event", AsyncMock())
    monkeypatch.setattr(distribution_api, "record_publish_outcome", MagicMock())
    resp = await dist_client.client.post("/api/distribution/publish-jobs/pj-1/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_retry_publish_job_not_found_after_claim(dist_client, monkeypatch):
    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def get_for_user(self, publish_job_id, user_id):
            return _publish_row(status="failed")

        async def retry_failed(self, publish_job_id):
            return None

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    resp = await dist_client.client.post("/api/distribution/publish-jobs/pj-1/retry")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_publish_progress_stream(dist_client, monkeypatch):
    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def get_for_user(self, publish_job_id, user_id):
            return _publish_row()

    async def fake_stream(job_id, cfg, last_event_id=None):
        yield 'event: progress\ndata: {"status":"processing"}\n\n'

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    monkeypatch.setattr(distribution_api, "stream_publish_progress", fake_stream)
    resp = await dist_client.client.get(
        "/api/distribution/publish-jobs/pj-1/progress",
        headers={"Last-Event-Id": "5"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")


# ─── update_publish_job (PATCH /api/distribution/publish-jobs/{id}) ───────────


@pytest.mark.asyncio
async def test_update_publish_job_not_found(dist_client, monkeypatch):
    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def get_for_user(self, publish_job_id, user_id):
            return None

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    resp = await dist_client.client.patch(
        "/api/distribution/publish-jobs/ghost",
        json={"title": "New Title"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_publish_job_invalid_status(dist_client, monkeypatch):
    """Jobs in terminal/active states cannot be edited."""
    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def get_for_user(self, publish_job_id, user_id):
            return _publish_row(status="published")

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    resp = await dist_client.client.patch(
        "/api/distribution/publish-jobs/pj-1",
        json={"title": "New Title"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_status"


@pytest.mark.asyncio
async def test_update_publish_job_reschedule_non_scheduled(dist_client, monkeypatch):
    """Setting scheduled_at on a 'pending' (not 'scheduled') job is rejected."""
    from datetime import datetime, timezone

    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def get_for_user(self, publish_job_id, user_id):
            return _publish_row(status="pending")

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    resp = await dist_client.client.patch(
        "/api/distribution/publish-jobs/pj-1",
        json={"scheduled_at": datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc).isoformat()},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_status"


@pytest.mark.asyncio
async def test_update_publish_job_race_conflict(dist_client, monkeypatch):
    """update_editable returns None when the job has already started uploading."""
    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def get_for_user(self, publish_job_id, user_id):
            return _publish_row(status="pending")

        async def update_editable(self, job_id, *, title, description, scheduled_at):
            return None

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    resp = await dist_client.client.patch(
        "/api/distribution/publish-jobs/pj-1",
        json={"title": "Too late"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "invalid_status"


@pytest.mark.asyncio
async def test_update_publish_job_success(dist_client, monkeypatch):
    """Happy-path: pending job can have its title/description updated."""
    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def get_for_user(self, publish_job_id, user_id):
            return _publish_row(status="pending")

        async def update_editable(self, job_id, *, title, description, scheduled_at):
            return _publish_row(status="pending", title=title or "T", description=description or "D")

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    resp = await dist_client.client.patch(
        "/api/distribution/publish-jobs/pj-1",
        json={"title": "Updated Title", "description": "Better desc"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"
    assert dist_client.session.committed


# ─── oauth_start / oauth_callback else (unknown adapter) ──────────────────────


@pytest.mark.asyncio
async def test_oauth_start_unknown_adapter_type(dist_client, monkeypatch):
    """If build_adapter returns an unrecognised adapter type, StreamClipError is raised."""
    class UnknownAdapter:
        pass

    with patch.object(distribution_api, "build_adapter", AsyncMock(return_value=UnknownAdapter())), \
         patch.object(distribution_api, "create_oauth_state", return_value="state"), \
         patch.object(distribution_api, "default_redirect_uri", return_value="http://cb"):
        resp = await dist_client.client.get("/api/distribution/oauth/youtube_shorts/start")

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_oauth_callback_unknown_adapter_type(dist_client, monkeypatch):
    """If build_adapter returns an unrecognised adapter, callback redirects to unknown_platform."""
    cfg = distribution_api.get_settings()
    web = cfg.distribution.web_origin.rstrip("/")

    class UnknownAdapter:
        pass

    with patch.object(distribution_api, "verify_oauth_state", return_value=USER_ID), \
         patch.object(distribution_api, "build_adapter", AsyncMock(return_value=UnknownAdapter())), \
         patch.object(distribution_api, "default_redirect_uri", return_value="http://cb"):
        resp = await dist_client.client.get(
            "/api/distribution/oauth/youtube_shorts/callback",
            params={"code": "abc", "state": "st"},
            follow_redirects=False,
        )

    assert resp.status_code in (302, 307)
    assert "unknown_platform" in resp.headers["location"]


# ─── residual OAuth / edit / progress edges (§3.7 H1) ─────────────────────────


@pytest.mark.asyncio
async def test_publish_progress_without_last_event_id(dist_client, monkeypatch):
    """No Last-Event-Id header → cursor stays None (branch 413→419)."""

    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def get_for_user(self, publish_job_id, user_id):
            return _publish_row()

    async def fake_stream(job_id, cfg, last_event_id=None):
        assert last_event_id is None
        yield 'event: progress\ndata: {"status":"pending"}\n\n'

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    monkeypatch.setattr(distribution_api, "stream_publish_progress", fake_stream)
    resp = await dist_client.client.get("/api/distribution/publish-jobs/pj-1/progress")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert "progress" in resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [
        {},  # missing code + state
        {"code": "only-code"},  # missing state
        {"state": "only-state"},  # missing code
    ],
)
async def test_oauth_callback_missing_code_or_state_denied(dist_client, params):
    """Provider callback without code/state is treated as oauth_denied (not oauth_failed)."""
    cfg = distribution_api.get_settings()
    web = cfg.distribution.web_origin.rstrip("/")
    resp = await dist_client.client.get(
        "/api/distribution/oauth/tiktok/callback",
        params=params,
        follow_redirects=False,
    )
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == f"{web}/distribution?error=oauth_denied"


@pytest.mark.asyncio
async def test_oauth_start_unknown_platform(dist_client):
    resp = await dist_client.client.get("/api/distribution/oauth/myspace/start")
    assert resp.status_code == 500
    assert resp.json()["code"] == "unknown_platform"


@pytest.mark.asyncio
async def test_update_oauth_app_unknown_platform(dist_client, monkeypatch):
    monkeypatch.setattr(distribution_api, "is_token_key_configured", lambda: True)
    resp = await dist_client.client.put(
        "/api/distribution/oauth-apps/myspace",
        json={"client_id": "abcd", "client_secret": "secret"},
    )
    assert resp.status_code == 500
    assert resp.json()["code"] == "unknown_platform"


@pytest.mark.asyncio
async def test_update_oauth_app_custom_redirect_uri(dist_client, monkeypatch, token_key):
    captured: dict = {}

    class FakeOAuthRepo:
        def __init__(self, db) -> None:
            pass

        async def upsert(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                client_id=kwargs["client_id"],
                redirect_uri=kwargs["redirect_uri"],
                client_secret_enc=kwargs["client_secret_enc"],
            )

    monkeypatch.setattr(distribution_api, "InstallOAuthAppRepository", FakeOAuthRepo)
    monkeypatch.setattr(distribution_api, "is_token_key_configured", lambda: True)
    custom = "https://app.example/oauth/youtube_shorts/callback"
    resp = await dist_client.client.put(
        "/api/distribution/oauth-apps/youtube_shorts",
        json={
            "client_id": "abcd",
            "client_secret": "secret",
            "redirect_uri": custom,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["redirect_uri"] == custom
    assert captured["redirect_uri"] == custom
    assert dist_client.session.committed


@pytest.mark.asyncio
async def test_list_oauth_apps_empty_redirect_uses_default(dist_client, monkeypatch):
    """Configured row with blank redirect_uri falls back to default_redirect_uri."""
    row = SimpleNamespace(
        client_id="cid",
        client_secret_enc="enc",
        redirect_uri="",
    )

    class FakeOAuthRepo:
        def __init__(self, db) -> None:
            pass

        async def get(self, platform):
            return row if platform == "youtube_shorts" else None

    monkeypatch.setattr(distribution_api, "InstallOAuthAppRepository", FakeOAuthRepo)
    monkeypatch.setattr(
        distribution_api,
        "default_redirect_uri",
        lambda platform, cfg: f"http://default/{platform}",
    )
    resp = await dist_client.client.get("/api/distribution/oauth-apps")
    assert resp.status_code == 200
    apps = {a["platform"]: a for a in resp.json()}
    assert apps["youtube_shorts"]["redirect_uri"] == "http://default/youtube_shorts"
    assert apps["youtube_shorts"]["configured"] is True
    assert apps["tiktok"]["redirect_uri"] == "http://default/tiktok"

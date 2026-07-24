"""HTTP contract tests for /api/distribution/* and /api/vault/*.

Repositories, services, and Celery are faked at the module boundary so these
exercise routing, auth dependencies, status codes, and error envelopes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import backend.api.distribution as distribution_api
import backend.api.vault as vault_api
from backend.db.models import UserTier
from backend.db.session import get_db
from backend.middleware.auth import get_current_user_id, require_user_id
from backend.middleware.distribution import require_distribution_access
from core.distribution.errors import NoConnectionError

USER_ID = "user-1"


class FakeSession:
    def __init__(self, users: dict[str, SimpleNamespace] | None = None) -> None:
        self.users = users or {}
        self.committed = False

    async def commit(self) -> None:
        self.committed = True

    async def get(self, model, pk):
        return self.users.get(pk)


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
        title="Title",
        description="Desc",
        error_message=None,
        last_error_code=None,
        created_at=datetime.now(timezone.utc),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _vault_row(**overrides) -> SimpleNamespace:
    base = dict(
        id="vc-1",
        user_id=USER_ID,
        title="Saved clip",
        hook="Hook",
        duration_secs=12.5,
        status="ready",
        source_clip_id=None,
        source_job_id=None,
        saved_at=datetime.now(timezone.utc),
        metadata_json={},
        storage_key="vault/clip.mp4",
        thumb_storage_key=None,
        file_size_bytes=5_000_000,
        archived_flag=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# ─── /api/distribution ────────────────────────────────────────────────────────

@pytest.fixture
def dist_client(app, client):
    session = FakeSession()

    async def fake_db():
        yield session

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[require_distribution_access] = lambda: USER_ID
    app.dependency_overrides[require_user_id] = lambda: USER_ID
    app.dependency_overrides[get_current_user_id] = lambda: None
    yield SimpleNamespace(client=client, session=session, app=app)
    for dep in (get_db, require_distribution_access, require_user_id, get_current_user_id):
        app.dependency_overrides.pop(dep, None)


@pytest.mark.asyncio
async def test_platforms_listing_anonymous(dist_client):
    resp = await dist_client.client.get("/api/distribution/platforms")
    assert resp.status_code == 200
    platforms = resp.json()
    ids = {p["id"] for p in platforms}
    assert "youtube_shorts" in ids
    assert all(p["connected"] is False for p in platforms)


@pytest.mark.asyncio
async def test_publish_now_returns_202(dist_client, monkeypatch):
    class FakeService:
        def __init__(self, db, cfg) -> None:
            pass

        async def publish_now(self, **kwargs):
            assert kwargs["user_id"] == USER_ID
            assert kwargs["clip_id"] == "clip-1"
            return _publish_row()

    monkeypatch.setattr(distribution_api, "DistributionService", FakeService)
    resp = await dist_client.client.post(
        "/api/distribution/publish",
        json={"clip_id": "clip-1", "platform": "youtube_shorts"},
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["id"] == "pj-1"
    assert body["status"] == "pending"
    assert dist_client.session.committed


@pytest.mark.asyncio
async def test_publish_now_maps_domain_error(dist_client, monkeypatch):
    class FailingService:
        def __init__(self, db, cfg) -> None:
            pass

        async def publish_now(self, **kwargs):
            raise NoConnectionError("youtube_shorts")

    monkeypatch.setattr(distribution_api, "DistributionService", FailingService)
    resp = await dist_client.client.post(
        "/api/distribution/publish",
        json={"clip_id": "clip-1", "platform": "youtube_shorts"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "NO_CONNECTION"


@pytest.mark.asyncio
async def test_publish_rejects_unknown_platform_at_schema(dist_client):
    resp = await dist_client.client.post(
        "/api/distribution/publish",
        json={"clip_id": "clip-1", "platform": "myspace"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_publish_jobs(dist_client, monkeypatch):
    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def list_for_user(self, user_id):
            return [_publish_row(), _publish_row(id="pj-2", status="published")]

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    resp = await dist_client.client.get("/api/distribution/publish-jobs")
    assert resp.status_code == 200
    assert [j["id"] for j in resp.json()] == ["pj-1", "pj-2"]


@pytest.mark.asyncio
async def test_retry_requires_failed_status(dist_client, monkeypatch):
    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def get_for_user(self, publish_job_id, user_id):
            return _publish_row(status="published")

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    resp = await dist_client.client.post("/api/distribution/publish-jobs/pj-1/retry")
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_status"


@pytest.mark.asyncio
async def test_retry_failed_job_requeues(dist_client, monkeypatch):
    delayed: list[str] = []

    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def get_for_user(self, publish_job_id, user_id):
            return _publish_row(status="failed")

        async def retry_failed(self, publish_job_id):
            return _publish_row(status="pending")

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    monkeypatch.setattr(
        distribution_api,
        "dispatch_task",
        lambda task, *, args=(), **kw: delayed.append(args[0]),
    )
    resp = await dist_client.client.post("/api/distribution/publish-jobs/pj-1/retry")
    assert resp.status_code == 202, resp.text
    assert delayed == ["pj-1"]


@pytest.mark.asyncio
async def test_retry_unknown_job_404(dist_client, monkeypatch):
    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def get_for_user(self, publish_job_id, user_id):
            return None

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    resp = await dist_client.client.post("/api/distribution/publish-jobs/ghost/retry")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cancel_rejects_terminal_status(dist_client, monkeypatch):
    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def get_for_user(self, publish_job_id, user_id):
            return _publish_row(status="published")

        async def cancel(self, publish_job_id):
            return None

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    resp = await dist_client.client.post("/api/distribution/publish-jobs/pj-1/cancel")
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_status"


@pytest.mark.asyncio
async def test_get_publish_job_scoped_to_owner(dist_client, monkeypatch):
    class FakeRepo:
        def __init__(self, db) -> None:
            pass

        async def get_for_user(self, publish_job_id, user_id):
            return _publish_row() if publish_job_id == "pj-1" else None

    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakeRepo)
    ok = await dist_client.client.get("/api/distribution/publish-jobs/pj-1")
    assert ok.status_code == 200
    missing = await dist_client.client.get("/api/distribution/publish-jobs/other")
    assert missing.status_code == 404


# ─── /api/vault ───────────────────────────────────────────────────────────────

class FakeVaultService:
    def __init__(self, db, cfg) -> None:
        pass

    def presigned_urls(self, row):
        return ("https://video", "https://thumb")

    async def save_clip_from_job(self, *, user_id, clip_id, title_override=None):
        return _vault_row(title=title_override or "Saved clip", source_clip_id=clip_id)


class FakeVaultPublishRepo:
    def __init__(self, db) -> None:
        pass

    async def list_for_vault_clip(self, vault_clip_id):
        return [_publish_row(vault_clip_id=vault_clip_id, status="published", external_url="https://yt")]

    @staticmethod
    def latest_per_platform(jobs):
        return jobs


@pytest.fixture
def vault_client(app, client, monkeypatch):
    user = SimpleNamespace(id=USER_ID, tier=UserTier.FREE)
    session = FakeSession(users={USER_ID: user})

    async def fake_db():
        yield session

    class FakeVaultRepo:
        rows: dict[str, SimpleNamespace] = {}
        deleted: list[str] = []

        def __init__(self, db) -> None:
            pass

        async def list_for_user(self, user_id):
            return [r for r in self.rows.values() if r.user_id == user_id]

        async def count_for_user(self, user_id):
            return len([
                r for r in self.rows.values()
                if r.user_id == user_id and not getattr(r, "archived_flag", False)
            ])

        async def bytes_for_user(self, user_id):
            return sum(
                getattr(r, "file_size_bytes", 0)
                for r in self.rows.values()
                if r.user_id == user_id and not getattr(r, "archived_flag", False)
            )

        async def get_for_user(self, vault_clip_id, user_id):
            row = self.rows.get(vault_clip_id)
            return row if row is not None and row.user_id == user_id else None

        async def delete(self, vault_clip_id):
            self.deleted.append(vault_clip_id)

    FakeVaultRepo.rows = {"vc-1": _vault_row()}
    FakeVaultRepo.deleted = []

    monkeypatch.setattr(vault_api, "VaultClipRepository", FakeVaultRepo)
    monkeypatch.setattr(vault_api, "VaultService", FakeVaultService)
    monkeypatch.setattr(vault_api, "PublishJobRepository", FakeVaultPublishRepo)
    monkeypatch.setattr(
        vault_api,
        "make_storage",
        lambda cfg: SimpleNamespace(delete=lambda key: None),
    )

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[require_user_id] = lambda: USER_ID
    yield SimpleNamespace(client=client, repo=FakeVaultRepo, session=session)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_user_id, None)


@pytest.mark.asyncio
async def test_list_vault_clips(vault_client):
    resp = await vault_client.client.get("/api/vault/clips")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["id"] == "vc-1"
    assert rows[0]["video_url"] == "https://video"
    assert rows[0]["publish_statuses"][0]["status"] == "published"


@pytest.mark.asyncio
async def test_vault_quota_reports_usage(vault_client):
    resp = await vault_client.client.get("/api/vault/quota")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["clips"]["used"] == 1
    assert body["clips"]["limit"] >= 0
    assert "bytes" in body
    assert body["bytes"]["used_human"]


@pytest.mark.asyncio
async def test_save_to_vault_returns_202(vault_client):
    resp = await vault_client.client.post(
        "/api/vault/clips",
        json={"clip_id": "clip-9", "title": "My best moment"},
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["title"] == "My best moment"
    assert body["source_clip_id"] == "clip-9"
    assert vault_client.session.committed


@pytest.mark.asyncio
async def test_delete_vault_clip(vault_client):
    resp = await vault_client.client.delete("/api/vault/clips/vc-1")
    assert resp.status_code == 204, resp.text
    assert vault_client.repo.deleted == ["vc-1"]


@pytest.mark.asyncio
async def test_delete_unknown_vault_clip_404(vault_client):
    resp = await vault_client.client.delete("/api/vault/clips/ghost")
    assert resp.status_code == 404

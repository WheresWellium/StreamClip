"""Editing queued/scheduled publish jobs and renaming vault clips."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import backend.api.distribution as distribution_api
import backend.api.vault as vault_api
from backend.db.session import get_db
from backend.middleware.auth import require_user_id
from backend.middleware.distribution import require_distribution_access

USER_ID = "user-1"


def _publish_row(status: str = "scheduled") -> SimpleNamespace:
    return SimpleNamespace(
        id="pj1",
        clip_id=None,
        vault_clip_id="vc1",
        platform="youtube_shorts",
        status=status,
        scheduled_at=datetime.now(timezone.utc) + timedelta(hours=2),
        published_at=None,
        external_id=None,
        external_url=None,
        title="Old title",
        description="Old description",
        error_message=None,
        last_error_code=None,
        created_at=datetime.now(timezone.utc),
    )


class FakePublishRepo:
    row: SimpleNamespace = _publish_row()

    def __init__(self, db) -> None:
        pass

    async def get_for_user(self, publish_job_id, user_id):
        if publish_job_id == self.row.id and user_id == USER_ID:
            return self.row
        return None

    async def update_editable(self, publish_job_id, *, title=None, description=None, scheduled_at=None):
        if self.row.status not in ("pending", "scheduled"):
            return None
        if title is not None:
            self.row.title = title
        if description is not None:
            self.row.description = description
        if scheduled_at is not None:
            self.row.scheduled_at = scheduled_at
        return self.row


class FakeSession:
    async def commit(self) -> None:
        pass


@pytest.fixture
def publish_env(app, monkeypatch):
    FakePublishRepo.row = _publish_row()
    monkeypatch.setattr(distribution_api, "PublishJobRepository", FakePublishRepo)

    async def fake_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[require_distribution_access] = lambda: USER_ID
    yield
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_distribution_access, None)


@pytest.mark.asyncio
async def test_edit_scheduled_publish_job(client, publish_env):
    new_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    resp = await client.patch(
        "/api/distribution/publish-jobs/pj1",
        json={"title": "New title", "scheduled_at": new_time},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"] == "New title"
    assert body["status"] == "scheduled"


@pytest.mark.asyncio
async def test_edit_rejects_published_job(client, publish_env):
    FakePublishRepo.row.status = "published"
    resp = await client.patch(
        "/api/distribution/publish-jobs/pj1",
        json={"title": "Too late"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_status"


@pytest.mark.asyncio
async def test_reschedule_rejected_for_pending_job(client, publish_env):
    FakePublishRepo.row.status = "pending"
    new_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    resp = await client.patch(
        "/api/distribution/publish-jobs/pj1",
        json={"scheduled_at": new_time},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_status"


@pytest.mark.asyncio
async def test_edit_unknown_job_404(client, publish_env):
    resp = await client.patch(
        "/api/distribution/publish-jobs/nope",
        json={"title": "x"},
    )
    assert resp.status_code == 404


# ─── Vault rename ────────────────────────────────────────────────────────────

def _vault_row() -> SimpleNamespace:
    return SimpleNamespace(
        id="vc1",
        title="Old name",
        hook="",
        duration_secs=12.0,
        status="ready",
        source_clip_id=None,
        source_job_id=None,
        saved_at=datetime.now(timezone.utc),
        metadata_json={},
    )


class FakeVaultRepo:
    row: SimpleNamespace = _vault_row()

    def __init__(self, db) -> None:
        pass

    async def rename(self, vault_clip_id, user_id, title):
        if vault_clip_id != self.row.id or user_id != USER_ID:
            return None
        self.row.title = title
        return self.row


class FakeVaultService:
    def __init__(self, db, cfg) -> None:
        pass

    def presigned_urls(self, row):
        return None, None


class FakeVaultPublishRepo:
    def __init__(self, db) -> None:
        pass

    async def list_for_vault_clip(self, vault_clip_id):
        return []

    @staticmethod
    def latest_per_platform(jobs):
        return []


@pytest.fixture
def vault_env(app, monkeypatch):
    FakeVaultRepo.row = _vault_row()
    monkeypatch.setattr(vault_api, "VaultClipRepository", FakeVaultRepo)
    monkeypatch.setattr(vault_api, "VaultService", FakeVaultService)
    monkeypatch.setattr(vault_api, "PublishJobRepository", FakeVaultPublishRepo)

    async def fake_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[require_user_id] = lambda: USER_ID
    yield
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_user_id, None)


@pytest.mark.asyncio
async def test_rename_vault_clip(client, vault_env):
    resp = await client.patch("/api/vault/clips/vc1", json={"title": "Fresh name"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["title"] == "Fresh name"


@pytest.mark.asyncio
async def test_rename_unknown_vault_clip_404(client, vault_env):
    resp = await client.patch("/api/vault/clips/ghost", json={"title": "x"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rename_empty_title_422(client, vault_env):
    resp = await client.patch("/api/vault/clips/vc1", json={"title": ""})
    assert resp.status_code == 422

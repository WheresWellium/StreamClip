"""Unit tests for DistributionService — gates, idempotency, ownership.

Repositories and the Celery task are faked so these run without Postgres/Redis.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import core.distribution.service as service_mod
from backend.db.models import ApprovalStatus, VaultClipStatus
from core.config import get_settings
from core.distribution.errors import (
    ClipNotApprovedError,
    ClipNotReadyError,
    DuplicateInFlightError,
    NoConnectionError,
    PlatformNotEnabledError,
    VideoTooLongError,
)
from core.distribution.service import DistributionService
from core.errors import StreamClipError

USER_ID = "user-1"
OTHER_USER = "user-2"
PLATFORM = "youtube_shorts"


def _clip(**overrides) -> SimpleNamespace:
    base = dict(
        id="clip-1",
        job_id="job-1",
        final_storage_key="clips/final.mp4",
        duration_secs=30.0,
        title="A clip",
        hook="A hook",
        approval_status=ApprovalStatus.APPROVED.value,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _vault_clip(**overrides) -> SimpleNamespace:
    base = dict(
        id="vc-1",
        user_id=USER_ID,
        storage_key="vault/final.mp4",
        duration_secs=30.0,
        title="Vault clip",
        hook="Vault hook",
        status=VaultClipStatus.READY.value,
        source_clip_id=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _connection(active: bool = True) -> SimpleNamespace:
    return SimpleNamespace(id="conn-1", platform=PLATFORM, is_active=active)


class FakeSession:
    async def flush(self) -> None:
        pass


class FakePublishRepo:
    def __init__(self) -> None:
        self.in_flight: SimpleNamespace | None = None
        self.by_idempotency: SimpleNamespace | None = None
        self.owned_ids: set[str] = set()
        self.created: list[dict] = []

    async def get_in_flight(self, *, clip_id, vault_clip_id, platform):
        return self.in_flight

    async def get_by_idempotency_key(self, key):
        return self.by_idempotency

    async def get_for_user(self, publish_job_id, user_id):
        if user_id == USER_ID and publish_job_id in self.owned_ids:
            return SimpleNamespace(id=publish_job_id)
        return None

    async def create(self, **fields):
        self.created.append(fields)
        return SimpleNamespace(id="pj-new", **fields)


class FakeConnRepo:
    def __init__(self, connection: SimpleNamespace | None) -> None:
        self.connection = connection

    async def get_by_platform(self, user_id, platform):
        return self.connection


class FakeClipRepo:
    def __init__(self, clips: dict[str, SimpleNamespace]) -> None:
        self.clips = clips

    async def get(self, clip_id, *, with_overlays=True):
        return self.clips.get(clip_id)


class FakeJobRepo:
    def __init__(self, jobs: dict[str, SimpleNamespace]) -> None:
        self.jobs = jobs

    async def get(self, job_id):
        return self.jobs.get(job_id)


class FakeVaultRepo:
    def __init__(self, rows: dict[str, SimpleNamespace]) -> None:
        self.rows = rows

    async def get_for_user(self, vault_clip_id, user_id):
        row = self.rows.get(vault_clip_id)
        if row is not None and row.user_id == user_id:
            return row
        return None


class FakeCeleryTask:
    def __init__(self) -> None:
        self.delayed: list[str] = []

    def delay(self, publish_job_id: str) -> None:
        self.delayed.append(publish_job_id)


@pytest.fixture
def env(monkeypatch):
    """A DistributionService wired to fakes, defaulting to a publishable clip."""
    celery = FakeCeleryTask()
    notified: list[str] = []

    async def fake_notify(db, job, *, event, cfg):
        notified.append(event)

    monkeypatch.setattr(service_mod, "publish_to_platform", celery)
    monkeypatch.setattr(service_mod, "notify_publish_event", fake_notify)

    svc = DistributionService.__new__(DistributionService)
    svc.db = FakeSession()
    svc.cfg = get_settings()
    svc.publish_repo = FakePublishRepo()
    svc.conn_repo = FakeConnRepo(_connection())
    svc.clip_repo = FakeClipRepo({"clip-1": _clip()})
    svc.job_repo = FakeJobRepo({"job-1": SimpleNamespace(id="job-1", owner_id=USER_ID)})
    svc.vault_repo = FakeVaultRepo({"vc-1": _vault_clip()})
    return SimpleNamespace(svc=svc, celery=celery, notified=notified)


# ─── Source selection ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_requires_exactly_one_source(env):
    with pytest.raises(StreamClipError) as exc:
        await env.svc.publish_now(user_id=USER_ID, platform=PLATFORM)
    assert exc.value.code == "invalid_source"

    with pytest.raises(StreamClipError) as exc:
        await env.svc.publish_now(
            user_id=USER_ID, clip_id="clip-1", vault_clip_id="vc-1", platform=PLATFORM,
        )
    assert exc.value.code == "invalid_source"


@pytest.mark.asyncio
async def test_unknown_platform_rejected(env):
    with pytest.raises(PlatformNotEnabledError):
        await env.svc.publish_now(user_id=USER_ID, clip_id="clip-1", platform="myspace")


# ─── Gates ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unapproved_clip_rejected(env):
    env.svc.clip_repo.clips["clip-1"] = _clip(approval_status=ApprovalStatus.DRAFT.value)
    with pytest.raises(ClipNotApprovedError):
        await env.svc.publish_now(user_id=USER_ID, clip_id="clip-1", platform=PLATFORM)


@pytest.mark.asyncio
async def test_unrendered_clip_rejected(env):
    env.svc.clip_repo.clips["clip-1"] = _clip(final_storage_key=None)
    with pytest.raises(ClipNotReadyError):
        await env.svc.publish_now(user_id=USER_ID, clip_id="clip-1", platform=PLATFORM)


@pytest.mark.asyncio
async def test_video_too_long_rejected(env):
    env.svc.clip_repo.clips["clip-1"] = _clip(duration_secs=61.0)
    with pytest.raises(VideoTooLongError):
        await env.svc.publish_now(user_id=USER_ID, clip_id="clip-1", platform=PLATFORM)


@pytest.mark.asyncio
async def test_missing_connection_rejected(env):
    env.svc.conn_repo = FakeConnRepo(None)
    with pytest.raises(NoConnectionError):
        await env.svc.publish_now(user_id=USER_ID, clip_id="clip-1", platform=PLATFORM)


@pytest.mark.asyncio
async def test_inactive_connection_rejected(env):
    env.svc.conn_repo = FakeConnRepo(_connection(active=False))
    with pytest.raises(NoConnectionError):
        await env.svc.publish_now(user_id=USER_ID, clip_id="clip-1", platform=PLATFORM)


@pytest.mark.asyncio
async def test_duplicate_in_flight_rejected(env):
    env.svc.publish_repo.in_flight = SimpleNamespace(id="pj-existing")
    with pytest.raises(DuplicateInFlightError) as exc:
        await env.svc.publish_now(user_id=USER_ID, clip_id="clip-1", platform=PLATFORM)
    assert exc.value.publish_job_id == "pj-existing"


# ─── Ownership ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clip_owned_by_other_user_is_404(env):
    env.svc.job_repo = FakeJobRepo({"job-1": SimpleNamespace(id="job-1", owner_id=OTHER_USER)})
    with pytest.raises(StreamClipError) as exc:
        await env.svc.publish_now(user_id=USER_ID, clip_id="clip-1", platform=PLATFORM)
    assert exc.value.http_status == 404


@pytest.mark.asyncio
async def test_vault_clip_owned_by_other_user_is_404(env):
    env.svc.vault_repo = FakeVaultRepo({"vc-1": _vault_clip(user_id=OTHER_USER)})
    with pytest.raises(StreamClipError) as exc:
        await env.svc.publish_now(user_id=USER_ID, vault_clip_id="vc-1", platform=PLATFORM)
    assert exc.value.http_status == 404


@pytest.mark.asyncio
async def test_vault_clip_not_ready_rejected(env):
    env.svc.vault_repo = FakeVaultRepo(
        {"vc-1": _vault_clip(status=VaultClipStatus.COPYING.value)},
    )
    with pytest.raises(ClipNotReadyError):
        await env.svc.publish_now(user_id=USER_ID, vault_clip_id="vc-1", platform=PLATFORM)


@pytest.mark.asyncio
async def test_vault_clip_with_unapproved_source_rejected(env):
    env.svc.vault_repo = FakeVaultRepo({"vc-1": _vault_clip(source_clip_id="clip-src")})
    env.svc.clip_repo = FakeClipRepo(
        {"clip-src": _clip(id="clip-src", approval_status=ApprovalStatus.REJECTED.value)},
    )
    with pytest.raises(ClipNotApprovedError):
        await env.svc.publish_now(user_id=USER_ID, vault_clip_id="vc-1", platform=PLATFORM)


# ─── Idempotency ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_idempotency_key_returns_existing_owned_job(env):
    existing = SimpleNamespace(id="pj-old")
    env.svc.publish_repo.by_idempotency = existing
    env.svc.publish_repo.owned_ids = {"pj-old"}
    job = await env.svc.publish_now(
        user_id=USER_ID, clip_id="clip-1", platform=PLATFORM, idempotency_key="key-1",
    )
    assert job.id == "pj-old"
    assert env.svc.publish_repo.created == []
    assert env.celery.delayed == []


@pytest.mark.asyncio
async def test_idempotency_key_of_other_user_conflicts(env):
    env.svc.publish_repo.by_idempotency = SimpleNamespace(id="pj-foreign")
    env.svc.publish_repo.owned_ids = set()  # not owned by USER_ID
    with pytest.raises(StreamClipError) as exc:
        await env.svc.publish_now(
            user_id=USER_ID, clip_id="clip-1", platform=PLATFORM, idempotency_key="key-1",
        )
    assert exc.value.code == "idempotency_conflict"
    assert exc.value.http_status == 409


# ─── Enqueue behaviour ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_publish_now_enqueues_pending_and_delays_task(env):
    job = await env.svc.publish_now(user_id=USER_ID, clip_id="clip-1", platform=PLATFORM)
    assert job.status == "pending"
    assert job.scheduled_at is None
    assert env.celery.delayed == [job.id]
    assert env.notified == []
    created = env.svc.publish_repo.created[0]
    assert created["title"] == "A clip"
    assert created["description"] == "A hook"
    assert created["connection_id"] == "conn-1"


@pytest.mark.asyncio
async def test_future_schedule_creates_scheduled_job_without_task(env):
    when = datetime.now(timezone.utc) + timedelta(hours=3)
    job = await env.svc.publish_now(
        user_id=USER_ID, clip_id="clip-1", platform=PLATFORM, scheduled_at=when,
    )
    assert job.status == "scheduled"
    assert job.scheduled_at == when
    assert env.celery.delayed == []
    assert env.notified == ["publish.scheduled"]


@pytest.mark.asyncio
async def test_past_schedule_publishes_immediately(env):
    when = datetime.now(timezone.utc) - timedelta(hours=1)
    job = await env.svc.publish_now(
        user_id=USER_ID, clip_id="clip-1", platform=PLATFORM, scheduled_at=when,
    )
    assert job.status == "pending"
    assert job.scheduled_at is None
    assert env.celery.delayed == [job.id]


@pytest.mark.asyncio
async def test_naive_schedule_treated_as_utc(env):
    naive = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=3)
    job = await env.svc.publish_now(
        user_id=USER_ID, clip_id="clip-1", platform=PLATFORM, scheduled_at=naive,
    )
    assert job.status == "scheduled"
    assert job.scheduled_at.tzinfo is not None


@pytest.mark.asyncio
async def test_title_truncated_to_platform_limit(env):
    long_title = "x" * 500
    job = await env.svc.publish_now(
        user_id=USER_ID, clip_id="clip-1", platform=PLATFORM, title=long_title,
    )
    assert len(job.title) == 100  # youtube_shorts title_max


# ─── verify_clip_in_job ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_clip_in_job_happy_path(env):
    clip = await env.svc.verify_clip_in_job("job-1", "clip-1", USER_ID)
    assert clip.id == "clip-1"


@pytest.mark.asyncio
async def test_verify_clip_in_job_wrong_owner(env):
    with pytest.raises(StreamClipError) as exc:
        await env.svc.verify_clip_in_job("job-1", "clip-1", OTHER_USER)
    assert exc.value.http_status == 404


@pytest.mark.asyncio
async def test_verify_clip_in_job_clip_from_other_job(env):
    env.svc.clip_repo.clips["clip-1"] = _clip(job_id="job-other")
    with pytest.raises(StreamClipError) as exc:
        await env.svc.verify_clip_in_job("job-1", "clip-1", USER_ID)
    assert exc.value.http_status == 404

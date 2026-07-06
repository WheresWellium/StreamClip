"""Unit tests for VaultService — gates, quota, presigned URLs."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import core.vault.service as vault_mod
from backend.db.models import ApprovalStatus, UserTier, VaultClipStatus
from core.config import get_settings
from core.distribution.errors import AlreadyInVaultError, ClipNotApprovedError, VaultFullError
from core.errors import StreamClipError
from core.vault.service import VaultService

USER = "user-1"
OTHER = "user-2"


def _clip(**overrides):
    base = dict(
        id="clip-1",
        job_id="job-1",
        final_storage_key="clips/final.mp4",
        thumbnail_storage_key="clips/thumb.jpg",
        approval_status=ApprovalStatus.APPROVED.value,
        title="Title",
        hook="Hook",
        duration_secs=12.0,
        ensemble_score=0.8,
        llm_score=0.7,
        emotion="hype",
        meme_keywords=["wow"],
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class FakeSession:
    async def get(self, model, pk):
        if pk == USER:
            return SimpleNamespace(id=USER, tier=UserTier.PRO)
        return None

    async def flush(self) -> None:
        pass


class FakeVaultRepo:
    def __init__(self) -> None:
        self.rows: list[SimpleNamespace] = []
        self.created: list[dict] = []

    async def get_by_source_clip(self, user_id, clip_id):
        for r in self.rows:
            if r.user_id == user_id and r.source_clip_id == clip_id:
                return r
        return None

    async def count_for_user(self, user_id):
        return len([r for r in self.rows if r.user_id == user_id])

    async def create(self, **fields):
        row = SimpleNamespace(id="vc-new", **fields)
        self.rows.append(row)
        self.created.append(fields)
        return row


class FakeClipRepo:
    def __init__(self, clip):
        self.clip = clip

    async def get(self, clip_id, *, with_overlays=True):
        return self.clip if clip_id == self.clip.id else None


class FakeJobRepo:
    def __init__(self, job):
        self.job = job

    async def get(self, job_id):
        return self.job


@pytest.fixture
def env(monkeypatch):
    celery = MagicMock()

    def _delay(*args, **kwargs):
        celery.delayed.append(args)

    celery.delayed = []
    celery.delay = _delay
    monkeypatch.setattr("core.tasks.vault_tasks.copy_clip_to_vault", celery)

    svc = VaultService.__new__(VaultService)
    svc.db = FakeSession()
    svc.cfg = get_settings()
    svc.vault_repo = FakeVaultRepo()
    svc.clip_repo = FakeClipRepo(_clip())
    svc.job_repo = FakeJobRepo(SimpleNamespace(id="job-1", owner_id=USER))
    svc.storage = SimpleNamespace(
        presigned_get_url=lambda key, expires_in: f"https://cdn/{key}",
    )
    return SimpleNamespace(svc=svc, celery=celery)


@pytest.mark.asyncio
async def test_save_clip_enqueues_copy(env):
    row = await env.svc.save_clip_from_job(user_id=USER, clip_id="clip-1")
    assert row.status == "copying"
    assert env.celery.delayed
    assert env.celery.delayed[0][0] == row.id


@pytest.mark.asyncio
async def test_save_rejects_unrendered(env):
    env.svc.clip_repo.clip = _clip(final_storage_key=None)
    with pytest.raises(StreamClipError) as exc:
        await env.svc.save_clip_from_job(user_id=USER, clip_id="clip-1")
    assert exc.value.code == "clip_not_ready"


@pytest.mark.asyncio
async def test_save_rejects_wrong_owner(env):
    env.svc.job_repo.job = SimpleNamespace(id="job-1", owner_id=OTHER)
    with pytest.raises(StreamClipError) as exc:
        await env.svc.save_clip_from_job(user_id=USER, clip_id="clip-1")
    assert exc.value.http_status == 404


@pytest.mark.asyncio
async def test_save_rejects_unapproved(env):
    env.svc.clip_repo.clip = _clip(approval_status=ApprovalStatus.DRAFT.value)
    with pytest.raises(ClipNotApprovedError):
        await env.svc.save_clip_from_job(user_id=USER, clip_id="clip-1")


@pytest.mark.asyncio
async def test_save_rejects_duplicate(env):
    env.svc.vault_repo.rows.append(
        SimpleNamespace(user_id=USER, source_clip_id="clip-1"),
    )
    with pytest.raises(AlreadyInVaultError):
        await env.svc.save_clip_from_job(user_id=USER, clip_id="clip-1")


@pytest.mark.asyncio
async def test_save_rejects_quota(env, monkeypatch):
    monkeypatch.setattr(
        vault_mod,
        "get_tier_limits",
        lambda tier: SimpleNamespace(max_vault_clips=0),
    )
    with pytest.raises(VaultFullError):
        await env.svc.save_clip_from_job(user_id=USER, clip_id="clip-1")


def test_presigned_urls_ready_only(env):
    ready = SimpleNamespace(
        storage_key="vault/v.mp4",
        thumb_storage_key="vault/t.jpg",
        status=VaultClipStatus.READY.value,
    )
    video, thumb = env.svc.presigned_urls(ready)
    assert video == "https://cdn/vault/v.mp4"
    assert thumb == "https://cdn/vault/t.jpg"

    copying = SimpleNamespace(
        storage_key="vault/v.mp4",
        thumb_storage_key=None,
        status=VaultClipStatus.COPYING.value,
    )
    assert env.svc.presigned_urls(copying) == (None, None)

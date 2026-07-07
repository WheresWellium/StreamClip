"""Publish notification helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.distribution import notify as notify_mod


@pytest.mark.asyncio
async def test_resolve_publish_job_owner_from_clip():
    clip = SimpleNamespace(job_id="job-1")
    job = SimpleNamespace(owner_id="owner-1")
    db = AsyncMock()
    db.get = AsyncMock(side_effect=lambda model, pk: clip if pk == "clip-1" else job)

    owner = await notify_mod.resolve_publish_job_owner_id(
        db,
        SimpleNamespace(clip_id="clip-1", vault_clip_id=None),
    )
    assert owner == "owner-1"


@pytest.mark.asyncio
async def test_resolve_publish_job_owner_from_vault():
    vault = SimpleNamespace(user_id="vault-owner")
    db = AsyncMock()
    db.get = AsyncMock(return_value=vault)

    owner = await notify_mod.resolve_publish_job_owner_id(
        db,
        SimpleNamespace(clip_id=None, vault_clip_id="vc-1"),
    )
    assert owner == "vault-owner"


@pytest.mark.asyncio
async def test_notify_publish_event_delivers():
    job = SimpleNamespace(
        id="pj-1",
        platform="youtube_shorts",
        status="published",
        clip_id="c1",
        vault_clip_id=None,
        external_url="https://yt/x",
        error_message=None,
        scheduled_at=datetime.now(timezone.utc),
    )
    user = SimpleNamespace(webhook_url="https://hooks/x", webhook_secret="sec")
    db = AsyncMock()
    db.get = AsyncMock(return_value=user)

    with patch.object(notify_mod, "resolve_publish_job_owner_id", AsyncMock(return_value="u1")), \
         patch.object(notify_mod, "deliver_publish_webhook", return_value=True):
        await notify_mod.notify_publish_event(db, job, event="publish.done")


def test_record_publish_outcome_histogram():
    notify_mod.record_publish_outcome(
        platform="youtube_shorts",
        status="succeeded",
        duration_secs=12.5,
    )
    notify_mod.record_publish_outcome(platform="tiktok", status="cancelled")

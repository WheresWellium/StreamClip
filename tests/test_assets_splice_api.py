"""Tests for the asset vault API and clip splice validation (MASTER_TODO 3.6)."""

from __future__ import annotations

import pytest

from backend.api.schemas import CreateJobRequest
from backend.db.models import ClipStatus, UserTier
from backend.db.repositories import ClipRepository, UserRepository
from backend.db.session import get_db
from backend.middleware.auth import get_current_user_id, require_user_id
from backend.middleware.scope import RequestScope
from backend.services.job_service import JobService
from core.config import get_settings
from core.errors import StreamClipError
from core.storage import LocalStorage

ANON = RequestScope(user_id=None, device_id="splicedevice0001")


# ─── /api/assets (HTTP, real DB) ──────────────────────────────────────────────

def _asset_body(name: str = "Explosion GIF") -> dict:
    return {
        "name": name,
        "asset_type": "gif",
        "storage_key": f"assets/{name.lower().replace(' ', '-')}.gif",
        "description": "A test overlay asset",
        "tags": ["boom"],
        "default_duration_secs": 2.0,
    }


@pytest.fixture
async def asset_user(db):
    users = UserRepository(db)
    user = await users.create(
        email=f"assets-{id(db)}@test.local",
        hashed_password="x",
        tier=UserTier.PRO,
    )
    await db.flush()
    return user


@pytest.fixture
async def assets_client(app, client, db, asset_user):
    async def use_test_db():
        yield db

    app.dependency_overrides[get_db] = use_test_db
    app.dependency_overrides[require_user_id] = lambda: asset_user.id
    app.dependency_overrides[get_current_user_id] = lambda: asset_user.id
    yield client
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_user_id, None)
    app.dependency_overrides.pop(get_current_user_id, None)


@pytest.mark.asyncio
async def test_create_list_delete_asset(assets_client):
    created = await assets_client.post("/api/assets", json=_asset_body())
    assert created.status_code == 201, created.text
    asset = created.json()
    assert asset["name"] == "Explosion GIF"
    assert asset["is_public"] is False

    listed = await assets_client.get("/api/assets")
    assert listed.status_code == 200
    assert any(a["id"] == asset["id"] for a in listed.json())

    deleted = await assets_client.delete(f"/api/assets/{asset['id']}")
    assert deleted.status_code == 204

    listed_after = await assets_client.get("/api/assets")
    assert all(a["id"] != asset["id"] for a in listed_after.json())


@pytest.mark.asyncio
async def test_create_asset_validates_body(assets_client):
    bad = await assets_client.post(
        "/api/assets",
        json={**_asset_body(), "asset_type": "exe"},
    )
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_delete_unknown_asset_404(assets_client):
    resp = await assets_client.delete("/api/assets/ghost")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_other_users_asset_404(assets_client, db):
    users = UserRepository(db)
    other = await users.create(
        email=f"other-{id(db)}@test.local", hashed_password="x", tier=UserTier.FREE,
    )
    from backend.db.models import Asset

    foreign = Asset(
        name="theirs",
        asset_type="png",
        storage_key="assets/theirs.png",
        description="not yours",
        is_public=False,
        owner_id=other.id,
    )
    db.add(foreign)
    await db.flush()

    resp = await assets_client.delete(f"/api/assets/{foreign.id}")
    assert resp.status_code == 404


# ─── Splice validation (JobService, real DB) ──────────────────────────────────

@pytest.fixture
def splice_env(tmp_path):
    cfg = get_settings(reload=True)
    return cfg, LocalStorage(tmp_path)


async def _make_job_with_clips(db, cfg, storage, *, n: int = 2, done: bool = True):
    svc = JobService(db, cfg, storage)
    job = await svc.create_job(CreateJobRequest(source_url="https://x"), ANON)
    clips = ClipRepository(db)
    made = []
    for i in range(n):
        clip = await clips.create(
            job_id=job.id,
            rank=i,
            start_secs=float(i * 10),
            end_secs=float(i * 10 + 5),
            title=f"Clip {i}",
        )
        if done:
            clip.status = ClipStatus.DONE
            clip.final_storage_key = f"clips/{i}.mp4"
        made.append(clip)
    await db.flush()
    return svc, job, made


@pytest.mark.asyncio
async def test_splice_creates_pending_merge_clip(db, splice_env):
    cfg, storage = splice_env
    svc, job, clips = await _make_job_with_clips(db, cfg, storage)
    merged = await svc.splice_clips(
        job.id, [c.id for c in clips], scope=ANON, transition="crossfade",
    )
    assert merged.kind == "splice"
    assert merged.status == ClipStatus.PENDING
    assert merged.parent_clip_ids == [c.id for c in clips]
    assert merged.start_secs == 0.0
    assert merged.end_secs == 15.0


@pytest.mark.asyncio
async def test_splice_requires_two_clips(db, splice_env):
    cfg, storage = splice_env
    svc, job, clips = await _make_job_with_clips(db, cfg, storage, n=1)
    with pytest.raises(StreamClipError):
        await svc.splice_clips(job.id, [clips[0].id], scope=ANON)


@pytest.mark.asyncio
async def test_splice_rejects_unrendered_clips(db, splice_env):
    cfg, storage = splice_env
    svc, job, clips = await _make_job_with_clips(db, cfg, storage, done=False)
    with pytest.raises(StreamClipError):
        await svc.splice_clips(job.id, [c.id for c in clips], scope=ANON)


@pytest.mark.asyncio
async def test_splice_rejects_mixed_aspect_ratios(db, splice_env):
    cfg, storage = splice_env
    svc, job, clips = await _make_job_with_clips(db, cfg, storage)
    clips[0].render_overrides = {"aspect_ratio": "1:1"}
    await db.flush()
    with pytest.raises(StreamClipError):
        await svc.splice_clips(job.id, [c.id for c in clips], scope=ANON)


@pytest.mark.asyncio
async def test_splice_ignores_existing_splice_clips(db, splice_env):
    """A splice clip can't be a parent of another splice."""
    cfg, storage = splice_env
    svc, job, clips = await _make_job_with_clips(db, cfg, storage)
    merged = await svc.splice_clips(job.id, [c.id for c in clips], scope=ANON)
    merged.status = ClipStatus.DONE
    merged.final_storage_key = "clips/merged.mp4"
    await db.flush()
    with pytest.raises(StreamClipError):
        await svc.splice_clips(job.id, [merged.id, clips[0].id], scope=ANON)

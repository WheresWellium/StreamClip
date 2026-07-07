"""Coverage batch — admin idempotency, license_link, clip words."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.api.schemas import ClipWordsOut
from backend.db.models import InstallLicense, User, UserTier
from backend.db.session import get_sessionmaker
from backend.middleware.scope import RequestScope
from backend.services.job_service import JobService
from backend.services.license_link import link_license_to_user, link_licenses_by_email
from core.models import Transcript, TranscriptSegment, Word

SCOPE = RequestScope(user_id=None, device_id="covbatch001")


def _unique_email() -> str:
    return f"batch6-{uuid.uuid4().hex[:10]}@example.com"


async def _register(client, *, tier: UserTier = UserTier.FREE) -> tuple[str, str]:
    email = _unique_email()
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "hunter2secure"},
    )
    assert resp.status_code == 201
    user_id = resp.json()["user"]["id"]
    token = resp.json()["access_token"]
    if tier != UserTier.FREE:
        SessionMaker = get_sessionmaker()
        async with SessionMaker() as session:
            user = await session.get(User, user_id)
            user.tier = tier
            await session.commit()
    return user_id, token


async def _seed_license(**overrides) -> str:
    SessionMaker = get_sessionmaker()
    async with SessionMaker() as session:
        lic = InstallLicense(
            license_key_hash=overrides.pop("license_key_hash", uuid.uuid4().hex[:64]),
            tier=UserTier.PRO,
            status=overrides.pop("status", "issued"),
            **overrides,
        )
        session.add(lic)
        await session.commit()
        return lic.id


@pytest.mark.asyncio
async def test_revoke_already_revoked_is_idempotent(client):
    _, admin_token = await _register(client, tier=UserTier.ADMIN)
    lic_id = await _seed_license()
    headers = {"Authorization": f"Bearer {admin_token}"}
    assert (await client.post(f"/api/admin/licenses/{lic_id}/revoke", headers=headers)).status_code == 200
    second = await client.post(f"/api/admin/licenses/{lic_id}/revoke", headers=headers)
    assert second.status_code == 200
    assert second.json()["status"] == "revoked"


@pytest.mark.asyncio
async def test_inactive_admin_cannot_revoke(client):
    user_id, admin_token = await _register(client, tier=UserTier.ADMIN)
    lic_id = await _seed_license()
    SessionMaker = get_sessionmaker()
    async with SessionMaker() as session:
        user = await session.get(User, user_id)
        user.is_active = False
        await session.commit()
    resp = await client.post(
        f"/api/admin/licenses/{lic_id}/revoke",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_link_license_to_user_upgrades_free_tier():
    user = SimpleNamespace(id="u1", tier=UserTier.FREE)
    lic = SimpleNamespace(id="l1", tier=UserTier.PRO)
    db = AsyncMock()
    repo = MagicMock()
    repo.link_user = AsyncMock()
    user_repo = MagicMock()
    user_repo.get = AsyncMock(return_value=user)

    with patch("backend.services.license_link.InstallLicenseRepository", return_value=repo), \
         patch("backend.services.license_link.UserRepository", return_value=user_repo):
        await link_license_to_user(db, lic, user.id)

    assert user.tier == UserTier.PRO


@pytest.mark.asyncio
async def test_link_licenses_by_email_syncs_tier():
    user = SimpleNamespace(id="u1", email="a@b.c", tier=UserTier.FREE)
    lic = SimpleNamespace(tier=UserTier.PRO)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=lic)))
    repo = MagicMock()
    repo.link_by_email = AsyncMock(return_value=1)

    with patch("backend.services.license_link.InstallLicenseRepository", return_value=repo):
        count = await link_licenses_by_email(db, user)

    assert count == 1
    assert user.tier == UserTier.PRO


def test_sync_tier_upgrades_free_only():
    from backend.services.license_link import _sync_tier

    free = SimpleNamespace(tier=UserTier.FREE)
    assert _sync_tier(free, UserTier.PRO) is True
    assert free.tier == UserTier.PRO
    pro = SimpleNamespace(tier=UserTier.PRO)
    assert _sync_tier(pro, UserTier.ADMIN) is False


@pytest.mark.asyncio
async def test_get_clip_words_returns_windowed_words():
    clip = SimpleNamespace(id="c1", start_secs=1.0, end_secs=3.0)
    job = SimpleNamespace(id="job-1", clips=[clip])
    transcript = Transcript(
        segments=(
            TranscriptSegment(
                id=0,
                text="hello world",
                start=0.5,
                end=2.5,
                speaker=None,
                words=(
                    Word(text="hello", start=0.5, end=1.2, probability=0.9),
                    Word(text="world", start=1.2, end=2.5, probability=0.85),
                ),
            ),
        ),
        language="en",
        duration=10.0,
        source_path=__import__("pathlib").Path("x"),
    )
    svc = JobService(MagicMock(), MagicMock(), MagicMock())
    svc.get_job = AsyncMock(return_value=job)
    svc.cfg = MagicMock()
    svc.cfg.caption.min_word_probability = 0.25
    svc.cfg.whisper.min_word_probability = 0.25

    with patch(
        "backend.services.job_service.load_persisted_job_transcript",
        return_value=transcript,
    ):
        out = await svc.get_clip_words("job-1", "c1", scope=SCOPE)

    assert isinstance(out, ClipWordsOut)
    assert len(out.words) == 2


@pytest.mark.asyncio
async def test_get_clip_words_404_when_transcript_missing():
    clip = SimpleNamespace(id="c1", start_secs=0.0, end_secs=5.0)
    job = SimpleNamespace(id="job-1", clips=[clip])
    svc = JobService(MagicMock(), MagicMock(), MagicMock())
    svc.get_job = AsyncMock(return_value=job)

    with patch(
        "backend.services.job_service.load_persisted_job_transcript",
        side_effect=FileNotFoundError("missing"),
    ):
        from core.errors import StreamClipError

        with pytest.raises(StreamClipError) as exc_info:
            await svc.get_clip_words("job-1", "c1", scope=SCOPE)
        assert exc_info.value.code == "transcript_not_ready"

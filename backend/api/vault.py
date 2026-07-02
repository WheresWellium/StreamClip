"""Clip Vault API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    ClipPublishStatusOut,
    SaveVaultClipRequest,
    UpdateVaultClipRequest,
    VaultClipOut,
    VaultQuotaOut,
)
from backend.db.models import User, UserTier, VaultClip
from backend.db.repositories import PublishJobRepository, VaultClipRepository
from backend.db.session import get_db
from backend.middleware.auth import require_user_id
from backend.middleware.rate_limit import rate_limit_request
from core.billing import get_tier_limits
from core.config import get_settings
from core.errors import StreamClipError
from core.storage import make_storage
from core.vault.service import VaultService

router = APIRouter(prefix="/api/vault", tags=["vault"])


async def _to_out(
    row: VaultClip,
    svc: VaultService,
    publish_repo: PublishJobRepository,
) -> VaultClipOut:
    video_url, thumb_url = svc.presigned_urls(row)
    latest = PublishJobRepository.latest_per_platform(
        await publish_repo.list_for_vault_clip(row.id),
    )
    publish_statuses = [
        ClipPublishStatusOut(
            platform=pj.platform,
            status=pj.status,
            publish_job_id=pj.id,
            external_url=pj.external_url,
        )
        for pj in latest
    ]
    return VaultClipOut(
        id=row.id,
        title=row.title,
        hook=row.hook,
        duration_secs=row.duration_secs,
        status=row.status,
        source_clip_id=row.source_clip_id,
        source_job_id=row.source_job_id,
        saved_at=row.saved_at,
        metadata_json=row.metadata_json or {},
        video_url=video_url,
        thumbnail_url=thumb_url,
        publish_statuses=publish_statuses,
    )


@router.get(
    "/clips",
    response_model=list[VaultClipOut],
    dependencies=[Depends(rate_limit_request)],
)
async def list_vault_clips(
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[VaultClipOut]:
    cfg = get_settings()
    svc = VaultService(db, cfg)
    repo = VaultClipRepository(db)
    publish_repo = PublishJobRepository(db)
    rows = await repo.list_for_user(user_id)
    return [await _to_out(r, svc, publish_repo) for r in rows]


@router.get(
    "/quota",
    response_model=VaultQuotaOut,
    dependencies=[Depends(rate_limit_request)],
)
async def vault_quota(
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VaultQuotaOut:
    user = await db.get(User, user_id)
    tier = user.tier if user else UserTier.FREE
    limits = get_tier_limits(tier)
    repo = VaultClipRepository(db)
    used = await repo.count_for_user(user_id)
    return VaultQuotaOut(used=used, limit=limits.max_vault_clips)


@router.post(
    "/clips",
    response_model=VaultClipOut,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_request)],
)
async def save_to_vault(
    body: SaveVaultClipRequest,
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VaultClipOut:
    cfg = get_settings()
    svc = VaultService(db, cfg)
    publish_repo = PublishJobRepository(db)
    row = await svc.save_clip_from_job(
        user_id=user_id,
        clip_id=body.clip_id,
        title_override=body.title,
    )
    await db.commit()
    return await _to_out(row, svc, publish_repo)


@router.patch(
    "/clips/{vault_clip_id}",
    response_model=VaultClipOut,
    dependencies=[Depends(rate_limit_request)],
)
async def update_vault_clip(
    vault_clip_id: str,
    body: UpdateVaultClipRequest,
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VaultClipOut:
    cfg = get_settings()
    svc = VaultService(db, cfg)
    repo = VaultClipRepository(db)
    publish_repo = PublishJobRepository(db)
    row = await repo.rename(vault_clip_id, user_id, body.title.strip())
    if row is None:
        raise StreamClipError(
            "Vault clip not found",
            user_message="Clip not found in your vault",
            http_status=404,
        )
    await db.commit()
    return await _to_out(row, svc, publish_repo)


@router.delete(
    "/clips/{vault_clip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit_request)],
)
async def delete_vault_clip(
    vault_clip_id: str,
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    cfg = get_settings()
    storage = make_storage(cfg)
    repo = VaultClipRepository(db)
    row = await repo.get_for_user(vault_clip_id, user_id)
    if row is None:
        raise StreamClipError("Vault clip not found", user_message="Clip not found in your vault")
    if row.storage_key:
        try:
            storage.delete(row.storage_key)
        except Exception:
            pass
    if row.thumb_storage_key:
        try:
            storage.delete(row.thumb_storage_key)
        except Exception:
            pass
    await repo.delete(vault_clip_id)
    await db.commit()

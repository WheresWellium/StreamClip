"""Per-user webhook settings and clip feedback."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    ClipFeedbackOut,
    ClipFeedbackRequest,
    PrivacySettingsOut,
    PrivacySettingsRequest,
    WebhookSettingsOut,
    WebhookSettingsRequest,
)
from backend.db.repositories import (
    ClipFeedbackRepository,
    ClipRepository,
    JobRepository,
    UserRepository,
)
from backend.db.session import get_db
from backend.middleware.auth import get_current_user_id, require_user_id
from backend.middleware.rate_limit import rate_limit_request
from backend.middleware.scope import RequestScope, get_request_scope
from backend.services.feedback_service import apply_clip_style_feedback
from core.config import get_settings
from core.errors import StreamClipError

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get(
    "/webhook",
    response_model=WebhookSettingsOut,
    dependencies=[Depends(rate_limit_request)],
)
async def get_webhook_settings(
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WebhookSettingsOut:
    user = await UserRepository(db).get(user_id)
    if user is None:
        raise StreamClipError("User not found")
    return WebhookSettingsOut(
        webhook_url=user.webhook_url,
        configured=bool(user.webhook_url),
    )


@router.put(
    "/webhook",
    response_model=WebhookSettingsOut,
    dependencies=[Depends(rate_limit_request)],
)
async def update_webhook_settings(
    body: WebhookSettingsRequest,
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WebhookSettingsOut:
    users = UserRepository(db)
    await users.update_webhook(
        user_id,
        webhook_url=body.webhook_url,
        webhook_secret=body.webhook_secret,
    )
    await db.commit()
    user = await users.get(user_id)
    return WebhookSettingsOut(
        webhook_url=user.webhook_url if user else None,
        configured=bool(user and user.webhook_url),
    )


@router.get(
    "/privacy",
    response_model=PrivacySettingsOut,
    dependencies=[Depends(rate_limit_request)],
)
async def get_privacy_settings(
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PrivacySettingsOut:
    user = await UserRepository(db).get(user_id)
    if user is None:
        raise StreamClipError("User not found")
    return PrivacySettingsOut(
        data_contribution_opt_in=user.data_contribution_opt_in,
    )


@router.put(
    "/privacy",
    response_model=PrivacySettingsOut,
    dependencies=[Depends(rate_limit_request)],
)
async def update_privacy_settings(
    body: PrivacySettingsRequest,
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PrivacySettingsOut:
    users = UserRepository(db)
    await users.set_data_contribution_opt_in(user_id, body.data_contribution_opt_in)
    await db.commit()
    return PrivacySettingsOut(
        data_contribution_opt_in=body.data_contribution_opt_in,
    )


@router.post(
    "/clips/{clip_id}/feedback",
    response_model=ClipFeedbackOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_request)],
)
async def submit_clip_feedback(
    clip_id: str,
    body: ClipFeedbackRequest,
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClipFeedbackOut:
    clips = ClipRepository(db)
    clip = await clips.get(clip_id, with_overlays=False)
    if clip is None:
        raise StreamClipError(
            "Clip not found",
            user_message="Clip not found",
            http_status=404,
        )

    cfg = get_settings()
    jobs = JobRepository(db)
    job = await jobs.get_for_scope(
        clip.job_id,
        owner_id=scope.user_id,
        device_id=scope.device_id,
        device_scoped=cfg.auth.device_scoped_anonymous,
    )
    if job is None:
        raise StreamClipError(
            "Clip not found",
            user_message="Clip not found",
            http_status=404,
        )

    fb_repo = ClipFeedbackRepository(db)
    await fb_repo.upsert(clip_id, user_id, body.rating)

    if user_id:
        await apply_clip_style_feedback(db, clip=clip, user_id=user_id, rating=body.rating)

    await db.commit()
    return ClipFeedbackOut(clip_id=clip_id, rating=body.rating)

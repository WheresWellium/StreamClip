"""Distribution hub — platform connections and publish queue."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    OAuthAppOut,
    OAuthAppUpdateRequest,
    OAuthStartResponse,
    PlatformConnectionOut,
    PublishJobOut,
    PublishNowRequest,
    SchedulePublishRequest,
    UpdatePublishJobRequest,
)
from backend.db.repositories import (
    InstallOAuthAppRepository,
    PlatformConnectionRepository,
    PublishJobRepository,
)
from backend.db.session import get_db
from backend.middleware.auth import get_current_user_id, require_user_id
from backend.middleware.distribution import require_distribution_access
from backend.middleware.rate_limit import rate_limit_request
from backend.services.sse import stream_publish_progress
from core.config import get_settings
from core.distribution.connections import save_platform_connection
from core.distribution.credentials import default_redirect_uri, resolve_oauth_app
from core.distribution.oauth_state import create_oauth_state, verify_oauth_state
from core.distribution.notify import notify_publish_event, record_publish_outcome
from core.distribution.registry import build_adapter, list_platforms
from core.distribution.service import DistributionService
from core.distribution.tokens import encrypt_secret, is_token_key_configured
from core.distribution.youtube import YouTubeShortsAdapter
from core.distribution.tiktok import TikTokAdapter
from core.errors import StreamClipError
from core.task_dispatch import dispatch_task
from core.tasks.publish_tasks import publish_to_platform

router = APIRouter(prefix="/api/distribution", tags=["distribution"])

VALID_PLATFORMS = frozenset({"youtube_shorts", "tiktok"})


def _ensure_platform(platform: str) -> None:
    if platform not in VALID_PLATFORMS:
        raise StreamClipError("Unknown platform", user_message="Unsupported platform.", code="unknown_platform")


@router.get("/platforms")
async def list_platforms_endpoint(
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, str | bool]]:
    conn_ids: set[str] = set()
    if user_id:
        repo = PlatformConnectionRepository(db)
        conn_ids = {c.platform for c in await repo.list_for_user(user_id)}
    return [
        {
            "id": p.id,
            "label": p.label,
            "enabled": p.enabled,
            "connected": p.id in conn_ids,
        }
        for p in list_platforms()
    ]


@router.get(
    "/oauth-apps",
    response_model=list[OAuthAppOut],
    dependencies=[Depends(rate_limit_request)],
)
async def list_oauth_apps(
    user_id: Annotated[str, Depends(require_distribution_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[OAuthAppOut]:
    cfg = get_settings()
    repo = InstallOAuthAppRepository(db)
    out: list[OAuthAppOut] = []
    for platform in VALID_PLATFORMS:
        row = await repo.get(platform)
        out.append(
            OAuthAppOut(
                platform=platform,
                client_id=row.client_id if row else "",
                redirect_uri=(row.redirect_uri if row and row.redirect_uri else default_redirect_uri(platform, cfg)),
                configured=bool(row and row.client_id and row.client_secret_enc),
            ),
        )
    return out


@router.put(
    "/oauth-apps/{platform}",
    response_model=OAuthAppOut,
    dependencies=[Depends(rate_limit_request)],
)
async def update_oauth_app(
    platform: str,
    body: OAuthAppUpdateRequest,
    user_id: Annotated[str, Depends(require_distribution_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OAuthAppOut:
    _ensure_platform(platform)
    if not is_token_key_configured():
        raise StreamClipError(
            "DISTRIBUTION_TOKEN_KEY not set",
            user_message="Server encryption key is not configured for OAuth secrets.",
            code="distribution_not_configured",
            http_status=503,
        )
    cfg = get_settings()
    redirect = body.redirect_uri or default_redirect_uri(platform, cfg)
    repo = InstallOAuthAppRepository(db)
    row = await repo.upsert(
        platform=platform,
        client_id=body.client_id.strip(),
        client_secret_enc=encrypt_secret(body.client_secret.strip()),
        redirect_uri=redirect,
    )
    await db.commit()
    return OAuthAppOut(
        platform=platform,
        client_id=row.client_id,
        redirect_uri=row.redirect_uri,
        configured=True,
    )


@router.get(
    "/oauth/{platform}/start",
    response_model=OAuthStartResponse,
    dependencies=[Depends(rate_limit_request)],
)
async def oauth_start(
    platform: str,
    user_id: Annotated[str, Depends(require_distribution_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OAuthStartResponse:
    _ensure_platform(platform)
    adapter = await build_adapter(db, platform)
    cfg = get_settings()
    redirect_uri = default_redirect_uri(platform, cfg)
    state = create_oauth_state(user_id, platform, cfg)
    if isinstance(adapter, YouTubeShortsAdapter):
        auth_url = await adapter.get_auth_url(redirect_uri, state=state)
    elif isinstance(adapter, TikTokAdapter):
        auth_url = await adapter.get_auth_url(redirect_uri, state=state)
    else:
        raise StreamClipError("Adapter not supported", code="unknown_platform")
    return OAuthStartResponse(auth_url=auth_url, platform=platform)


@router.get("/oauth/{platform}/callback")
async def oauth_callback(
    platform: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    _ensure_platform(platform)
    cfg = get_settings()
    web = cfg.distribution.web_origin.rstrip("/")
    if error or not code or not state:
        return RedirectResponse(f"{web}/distribution?error=oauth_denied")
    try:
        user_id = verify_oauth_state(state, platform, cfg)
        adapter = await build_adapter(db, platform)
        redirect_uri = default_redirect_uri(platform, cfg)
        if isinstance(adapter, YouTubeShortsAdapter):
            creds = await adapter.exchange_code(code, redirect_uri)
            label = await adapter.fetch_channel_label(creds.access_token)
        elif isinstance(adapter, TikTokAdapter):
            creds = await adapter.exchange_code(code, redirect_uri)
            label = await adapter.fetch_user_label(creds.access_token)
        else:
            return RedirectResponse(f"{web}/distribution?error=unknown_platform")
        await save_platform_connection(
            db,
            user_id=user_id,
            platform=platform,
            account_label=label,
            credentials=creds,
        )
        await db.commit()
        return RedirectResponse(f"{web}/distribution?connected={platform}")
    except StreamClipError:
        return RedirectResponse(f"{web}/distribution?error=oauth_failed")
    except Exception:
        return RedirectResponse(f"{web}/distribution?error=oauth_failed")


@router.get(
    "/connections",
    response_model=list[PlatformConnectionOut],
    dependencies=[Depends(rate_limit_request)],
)
async def list_connections(
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PlatformConnectionOut]:
    repo = PlatformConnectionRepository(db)
    conns = await repo.list_for_user(user_id)
    return [PlatformConnectionOut.model_validate(c) for c in conns]


@router.delete(
    "/connections/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit_request)],
)
async def disconnect_platform(
    connection_id: str,
    user_id: Annotated[str, Depends(require_distribution_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    repo = PlatformConnectionRepository(db)
    conn = await repo.deactivate(connection_id, user_id)
    if conn is None:
        raise StreamClipError("Connection not found", user_message="Connection not found")
    await db.commit()


@router.get(
    "/publish-jobs",
    response_model=list[PublishJobOut],
    dependencies=[Depends(rate_limit_request)],
)
async def list_publish_jobs(
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PublishJobOut]:
    repo = PublishJobRepository(db)
    jobs = await repo.list_for_user(user_id)
    return [PublishJobOut.model_validate(j) for j in jobs]


@router.post(
    "/publish",
    response_model=PublishJobOut,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_request)],
)
async def publish_now(
    body: PublishNowRequest,
    user_id: Annotated[str, Depends(require_distribution_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublishJobOut:
    cfg = get_settings()
    svc = DistributionService(db, cfg)
    job = await svc.publish_now(
        user_id=user_id,
        clip_id=body.clip_id,
        vault_clip_id=body.vault_clip_id,
        platform=body.platform,
        title=body.title,
        description=body.description,
        scheduled_at=body.scheduled_at,
        idempotency_key=body.idempotency_key,
    )
    await db.commit()
    return PublishJobOut.model_validate(job)


@router.post(
    "/publish-jobs/{publish_job_id}/retry",
    response_model=PublishJobOut,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_request)],
)
async def retry_publish_job(
    publish_job_id: str,
    user_id: Annotated[str, Depends(require_distribution_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublishJobOut:
    repo = PublishJobRepository(db)
    existing = await repo.get_for_user(publish_job_id, user_id)
    if existing is None:
        raise StreamClipError("Publish job not found", user_message="Publish job not found", http_status=404)
    if existing.status != "failed":
        raise StreamClipError(
            "Cannot retry",
            user_message="Only failed publish jobs can be retried.",
            code="invalid_status",
            http_status=400,
        )
    job = await repo.retry_failed(publish_job_id)
    if job is None:
        raise StreamClipError("Retry failed", user_message="Could not retry publish job.", http_status=409)
    dispatch_task(publish_to_platform, args=(job.id,))
    await db.commit()
    return PublishJobOut.model_validate(job)


@router.post(
    "/publish-jobs/{publish_job_id}/cancel",
    response_model=PublishJobOut,
    dependencies=[Depends(rate_limit_request)],
)
async def cancel_publish_job(
    publish_job_id: str,
    user_id: Annotated[str, Depends(require_distribution_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublishJobOut:
    repo = PublishJobRepository(db)
    existing = await repo.get_for_user(publish_job_id, user_id)
    if existing is None:
        raise StreamClipError("Publish job not found", user_message="Publish job not found", http_status=404)
    job = await repo.cancel(publish_job_id)
    if job is None:
        raise StreamClipError(
            "Cannot cancel",
            user_message="Only scheduled or pending jobs can be cancelled.",
            code="invalid_status",
            http_status=400,
        )
    await notify_publish_event(db, job, event="publish.cancelled", cfg=get_settings())
    record_publish_outcome(platform=job.platform, status="cancelled")
    await db.commit()
    return PublishJobOut.model_validate(job)


@router.patch(
    "/publish-jobs/{publish_job_id}",
    response_model=PublishJobOut,
    dependencies=[Depends(rate_limit_request)],
)
async def update_publish_job(
    publish_job_id: str,
    body: UpdatePublishJobRequest,
    user_id: Annotated[str, Depends(require_distribution_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublishJobOut:
    """Edit title/description/schedule of a queued or scheduled publish."""
    repo = PublishJobRepository(db)
    existing = await repo.get_for_user(publish_job_id, user_id)
    if existing is None:
        raise StreamClipError("Publish job not found", user_message="Publish job not found", http_status=404)
    if existing.status not in ("pending", "scheduled"):
        raise StreamClipError(
            "Cannot edit",
            user_message="Only queued or scheduled publishes can be edited.",
            code="invalid_status",
            http_status=400,
        )
    if body.scheduled_at is not None and existing.status != "scheduled":
        raise StreamClipError(
            "Cannot reschedule",
            user_message="Only scheduled publishes can be rescheduled.",
            code="invalid_status",
            http_status=400,
        )
    job = await repo.update_editable(
        publish_job_id,
        title=body.title,
        description=body.description,
        scheduled_at=body.scheduled_at,
    )
    if job is None:
        raise StreamClipError(
            "Edit failed",
            user_message="The publish job started uploading — edits are no longer possible.",
            code="invalid_status",
            http_status=409,
        )
    await db.commit()
    return PublishJobOut.model_validate(job)


@router.get(
    "/publish-jobs/{publish_job_id}",
    response_model=PublishJobOut,
    dependencies=[Depends(rate_limit_request)],
)
async def get_publish_job(
    publish_job_id: str,
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublishJobOut:
    repo = PublishJobRepository(db)
    job = await repo.get_for_user(publish_job_id, user_id)
    if job is None:
        raise StreamClipError("Publish job not found", user_message="Publish job not found", http_status=404)
    return PublishJobOut.model_validate(job)


@router.get(
    "/publish-jobs/{publish_job_id}/progress",
    response_class=StreamingResponse,
    dependencies=[Depends(rate_limit_request)],
)
async def publish_progress_stream(
    publish_job_id: str,
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    last_event_id: Annotated[str | None, Header(alias="Last-Event-Id")] = None,
) -> StreamingResponse:
    repo = PublishJobRepository(db)
    job = await repo.get_for_user(publish_job_id, user_id)
    if job is None:
        raise StreamClipError("Publish job not found", user_message="Publish job not found", http_status=404)

    cfg = get_settings()
    cursor: int | None = None
    if last_event_id:
        try:
            cursor = int(last_event_id)
        except ValueError:
            cursor = None

    generator = stream_publish_progress(publish_job_id, cfg, last_event_id=cursor)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post(
    "/schedule",
    response_model=PublishJobOut,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit_request)],
)
async def schedule_publish(
    body: SchedulePublishRequest,
    user_id: Annotated[str, Depends(require_distribution_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublishJobOut:
    cfg = get_settings()
    svc = DistributionService(db, cfg)
    job = await svc.publish_now(
        user_id=user_id,
        clip_id=body.clip_id,
        vault_clip_id=body.vault_clip_id,
        platform=body.platform,
        title=body.title,
        description=body.description,
        scheduled_at=body.scheduled_at,
    )
    await db.commit()
    return PublishJobOut.model_validate(job)

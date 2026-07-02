"""
StreamClip — Upload API Router

Direct browser → object-storage uploads via presigned PUT URLs.
The API never sees the bytes — Next.js calls `POST /api/uploads/init`,
gets a presigned URL, then uploads directly to S3/MinIO.

Endpoints:
  POST /api/uploads/init     — Get presigned PUT URL + storage key
  GET  /api/uploads/{key}    — Get presigned GET URL for an existing key
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import UploadInitRequest, UploadInitResponse
from backend.db.session import get_db
from backend.middleware.scope import RequestScope, get_request_scope
from backend.middleware.rate_limit import rate_limit_request
from backend.services.job_service import UploadService
from core.config import get_settings
from core.storage import make_storage

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post(
    "/init",
    response_model=UploadInitResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_request)],
)
async def init_upload(
    body: UploadInitRequest,
    scope: Annotated[RequestScope, Depends(get_request_scope)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UploadInitResponse:
    """
    Initialise a direct upload. The client then PUTs the file bytes
    straight to the returned `upload_url`, then references `storage_key`
    when creating a job.
    """
    cfg = get_settings()
    svc = UploadService(cfg, make_storage(cfg))
    return await svc.init_upload(body, scope)


@router.get(
    "/url",
    dependencies=[Depends(rate_limit_request)],
)
async def get_download_url(
    key: str = Query(..., description="Storage key"),
    user_id: Annotated[str | None, Depends(get_current_user_id)] = None,
) -> dict[str, str]:
    """Get a fresh presigned download URL for a given storage key."""
    cfg = get_settings()
    storage = make_storage(cfg)
    url = storage.presigned_get_url(key, expires_in=cfg.storage.presigned_expiry_secs)
    return {"url": url, "expires_in": str(cfg.storage.presigned_expiry_secs)}

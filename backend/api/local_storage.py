"""
Local filesystem storage HTTP surface (ADR-001 §4.3).

When ``storage.backend=local``, presigned URLs point at ``/storage/{key}``.
Browsers upload via PUT with ``?upload=1``; downloads use GET.
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, Response

from backend.middleware.rate_limit import rate_limit_request
from core.config import Settings, get_settings
from core.storage import LocalStorage, make_storage

log = structlog.get_logger(__name__)

router = APIRouter(tags=["storage"])


def _local_storage(cfg: Settings | None = None) -> LocalStorage:
    storage = make_storage(cfg or get_settings())
    if not isinstance(storage, LocalStorage):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Local storage route is only available when storage.backend=local",
        )
    return storage


@router.get(
    "/storage/{key:path}",
    dependencies=[Depends(rate_limit_request)],
)
async def get_local_object(key: str) -> FileResponse:
    """Serve a file from local storage (desktop / dev profile)."""
    store = _local_storage()
    if not store.exists(key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    path = store._abs(key)
    media_type = "application/octet-stream"
    if key.endswith(".mp4"):
        media_type = "video/mp4"
    elif key.endswith((".jpg", ".jpeg")):
        media_type = "image/jpeg"
    elif key.endswith(".png"):
        media_type = "image/png"
    elif key.endswith(".webp"):
        media_type = "image/webp"
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.put(
    "/storage/{key:path}",
    dependencies=[Depends(rate_limit_request)],
)
async def put_local_object(
    key: str,
    request: Request,
    upload: Annotated[int | None, Query()] = None,
) -> Response:
    """Accept a direct browser upload for local storage."""
    if upload is None:
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="Use PUT with ?upload=1 for direct uploads",
        )
    store = _local_storage()
    dest = store._abs(key)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        body = await request.body()
        dest.write_bytes(body)
    except OSError as exc:
        log.warning("local_storage_put_failed", key=key, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed",
        ) from exc
    log.debug("local_storage_put", key=key, size=dest.stat().st_size)
    return Response(status_code=status.HTTP_200_OK)

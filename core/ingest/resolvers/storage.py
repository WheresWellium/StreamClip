"""Storage-backed ingest — MinIO/S3 uploads."""

from __future__ import annotations

from pathlib import Path

import structlog

from core.config import Settings
from core.errors import IngestError, StorageError
from core.ingest.probe import probe_video
from core.models import VideoMeta
from core.storage import Storage, make_storage

log = structlog.get_logger(__name__)


def download_from_storage(
    storage_key: str,
    local_dest: Path,
    cfg: Settings,
    storage: Storage | None = None,
) -> VideoMeta:
    """Pull an uploaded object into the job workspace."""
    store = storage or make_storage(cfg)
    local_dest.parent.mkdir(parents=True, exist_ok=True)

    if not local_dest.exists():
        try:
            store.download(storage_key, local_dest)
        except StorageError as exc:
            raise IngestError(
                f"Failed to download upload {storage_key}",
                user_message="Uploaded file not found in storage. Try uploading again.",
            ) from exc

    meta = probe_video(local_dest)
    log.info("ingest_upload_resolved", storage_key=storage_key, duration_secs=meta.duration)
    return VideoMeta(**{**vars(meta), "path": local_dest})

"""Storage-backed ingest — MinIO/S3 uploads."""

from __future__ import annotations

from collections.abc import Callable
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
    on_progress: Callable[[float], None] | None = None,
) -> VideoMeta:
    """Pull an uploaded object into the job workspace."""
    store = storage or make_storage(cfg)
    local_dest.parent.mkdir(parents=True, exist_ok=True)

    if not local_dest.exists():
        try:
            total_bytes = store.size(storage_key)

            def _bytes_progress(done: int, total: int) -> None:
                if on_progress and total > 0:
                    on_progress(min(done / total, 1.0))

            store.download(storage_key, local_dest, on_progress=_bytes_progress)
        except (StorageError, FileNotFoundError, OSError) as exc:
            # LocalStorage.size/download raise FileNotFoundError when the PUT
            # never landed; map to the same friendly upload-again copy.
            raise IngestError(
                f"Failed to download upload {storage_key}",
                user_message="Uploaded file not found in storage. Try uploading again.",
            ) from exc
    elif on_progress:
        on_progress(1.0)

    meta = probe_video(local_dest)
    log.info(
        "ingest_upload_resolved",
        storage_key=storage_key,
        duration_secs=meta.duration,
        size_bytes=local_dest.stat().st_size if local_dest.exists() else 0,
    )
    return VideoMeta(**{**vars(meta), "path": local_dest})

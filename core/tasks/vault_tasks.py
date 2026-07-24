"""Celery tasks for Clip Vault."""

from __future__ import annotations

import tempfile
from pathlib import Path

import structlog

from backend.db.models import VaultClip
from backend.db.repositories import VaultClipRepository
from core.celery_app import celery_app
from core.config import get_settings
from backend.db.session import db_session
from core.pipeline_metrics import VAULT_SAVES_TOTAL
from core.storage import make_storage, vault_clip_key
from core.tasks.pipeline_tasks import _safe_async

log = structlog.get_logger(__name__)
cfg = get_settings()


@celery_app.task(name="core.tasks.vault_tasks.copy_clip_to_vault")
def copy_clip_to_vault(
    vault_clip_id: str,
    source_video_key: str,
    source_thumb_key: str | None,
) -> dict[str, str]:
    """Copy rendered clip bytes into durable vault prefix."""

    async def _do() -> dict[str, str]:
        storage = make_storage(cfg)
        async with db_session() as db:
            row = await db.get(VaultClip, vault_clip_id)
            if row is None:
                return {"status": "error", "message": "vault clip not found"}

            video_dest = vault_clip_key(row.user_id, vault_clip_id, "clip.mp4")
            thumb_dest = vault_clip_key(row.user_id, vault_clip_id, "thumb.jpg")

            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                local_video = tmp_path / "clip.mp4"
                storage.download(source_video_key, local_video)
                video_bytes = local_video.stat().st_size
                storage.upload(video_dest, local_video, content_type="video/mp4")

                saved_thumb: str | None = None
                if source_thumb_key and storage.exists(source_thumb_key):
                    local_thumb = tmp_path / "thumb.jpg"
                    storage.download(source_thumb_key, local_thumb)
                    storage.upload(thumb_dest, local_thumb, content_type="image/jpeg")
                    saved_thumb = thumb_dest

            repo = VaultClipRepository(db)
            await repo.update_status(
                vault_clip_id,
                status="ready",
                storage_key=video_dest,
                thumb_storage_key=saved_thumb,
                file_size_bytes=video_bytes,
            )
            await db.commit()
            log.info("vault_clip_saved", vault_clip_id=vault_clip_id, key=video_dest)
            VAULT_SAVES_TOTAL.labels(status="ready").inc()
            return {"status": "ready", "vault_clip_id": vault_clip_id}

    try:
        return _safe_async(_do())
    except Exception as exc:
        log.exception("vault_copy_failed", vault_clip_id=vault_clip_id, error=str(exc))

        async def _fail() -> None:
            async with db_session() as db:
                repo = VaultClipRepository(db)
                await repo.update_status(vault_clip_id, status="failed")
                await db.commit()

        _safe_async(_fail())
        VAULT_SAVES_TOTAL.labels(status="failed").inc()
        return {"status": "failed", "vault_clip_id": vault_clip_id, "error": str(exc)}

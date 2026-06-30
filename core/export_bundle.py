"""Build a ZIP archive of finished job clips for bulk download."""

from __future__ import annotations

import io
import re
import tempfile
import zipfile
from pathlib import Path

import structlog

from backend.db.models import Job
from core.storage import Storage

log = structlog.get_logger(__name__)


def _safe_filename(title: str, rank: int) -> str:
    base = re.sub(r"[^\w\s-]", "", title or f"clip_{rank + 1}").strip()
    base = re.sub(r"\s+", "_", base)[:48] or f"clip_{rank + 1:02d}"
    return f"{rank + 1:02d}_{base}.mp4"


def build_job_clips_zip(job: Job, storage: Storage) -> bytes:
    """
    Download each finished clip from storage and pack into an in-memory ZIP.

    Skips clips without a ``final_storage_key``.
    """
    buf = io.BytesIO()
    added = 0
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for clip in sorted(job.clips, key=lambda c: c.rank):
            if not clip.final_storage_key:
                continue
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            try:
                storage.download(clip.final_storage_key, tmp_path)
                zf.write(tmp_path, arcname=_safe_filename(clip.title, clip.rank))
                added += 1
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()
    if added == 0:
        raise ValueError("No rendered clips available to export")
    log.info("job_zip_built", job_id=job.id, clip_count=added)
    return buf.getvalue()

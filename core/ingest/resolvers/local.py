"""Local file ingest resolver."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import structlog

from core.config import Settings
from core.ingest.probe import probe_video
from core.models import VideoMeta

log = structlog.get_logger(__name__)


def _file_hash(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def resolve_local(src: Path, workspace_dest: Path, cfg: Settings) -> VideoMeta:
    """Copy local file into job workspace and probe."""
    src = src.resolve()
    if not src.exists():
        raise FileNotFoundError(f"Local video not found: {src}")

    workspace_dest.parent.mkdir(parents=True, exist_ok=True)
    if not workspace_dest.exists():
        log.info("ingest_local_copy", src=str(src), dst=str(workspace_dest))
        shutil.copy2(src, workspace_dest)

    meta = probe_video(workspace_dest)
    log.info(
        "ingest_local_complete",
        title=meta.title,
        duration_secs=meta.duration,
    )
    return VideoMeta(**{**vars(meta), "path": workspace_dest})

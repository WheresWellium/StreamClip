"""
StreamClip — Ingest (legacy module path)

Delegates to core.ingest package. Import from here or core.ingest interchangeably.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path

from core.config import Settings
from core.ingest.probe import probe_video
from core.ingest.resolvers.url import download_url
from core.ingest.service import IngestService
from core.ingest.types import IngestRequest
from core.models import VideoMeta

__all__ = ["ingest", "ingest_local", "download", "probe_video", "IngestService"]


def download(
    url: str,
    cfg: Settings,
    on_progress: Callable[[float], None] | None = None,
) -> VideoMeta:
    from core.ingest.classifier import classify_url
    from core.ingest.types import ProcessingTier

    tier = classify_url(url)
    return download_url(url, cfg, tier=tier, on_progress=on_progress)[0]


def ingest_local(path: str | Path, cfg: Settings) -> VideoMeta:
    job_id = f"local-{uuid.uuid4().hex[:8]}"
    svc = IngestService(cfg)
    result = svc.run(IngestRequest(job_id=job_id, local_path=Path(path)))
    return result.meta


def ingest(
    source: str | Path,
    cfg: Settings,
    on_progress: Callable[[float], None] | None = None,
    *,
    job_id: str | None = None,
) -> VideoMeta:
    """Unified ingest for CLI and legacy callers."""
    jid = job_id or f"adhoc-{uuid.uuid4().hex[:8]}"
    s = str(source)
    if s.startswith(("http://", "https://", "twitch.tv", "www.")):
        req = IngestRequest(job_id=jid, source_url=s)
    else:
        req = IngestRequest(job_id=jid, local_path=Path(source))
    return IngestService(cfg).run(req, on_progress=on_progress).meta

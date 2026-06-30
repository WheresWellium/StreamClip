"""Ingest orchestrator — single entry for all source types."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import structlog

from core.config import Settings
from core.ingest.classifier import resolve_tier
from core.ingest.resolvers.local import resolve_local
from core.ingest.resolvers.storage import download_from_storage
from core.ingest.resolvers.url import download_url
from core.ingest.types import IngestRequest, IngestResult, SourceKind
from core.models import VideoMeta
from core.storage import Storage, job_key, make_storage

log = structlog.get_logger(__name__)

CANONICAL_SOURCE_NAME = "source.mp4"


class IngestService:
    """
    Modular ingest facade.

    Every source type resolves to:
      • one canonical local file in the job workspace
      • probed VideoMeta
      • a processing tier for downstream cost control
      • optional durable storage key (uploads keep original key; URLs get job copy)
    """

    def __init__(self, cfg: Settings, storage: Storage | None = None) -> None:
        self.cfg = cfg
        self.storage = storage or make_storage(cfg)

    def _workspace_source(self, job_id: str) -> Path:
        return self.cfg.workspace_dir / "jobs" / job_id / CANONICAL_SOURCE_NAME

    def run(
        self,
        request: IngestRequest,
        on_progress: Callable[[float], None] | None = None,
    ) -> IngestResult:
        local_path = self._workspace_source(request.job_id)
        kind = request.kind

        if kind == SourceKind.UPLOAD:
            assert request.storage_key
            meta = download_from_storage(
                request.storage_key, local_path, self.cfg, self.storage,
            )
            storage_key = request.storage_key

        elif kind == SourceKind.URL:
            assert request.source_url
            url = request.source_url
            if url.startswith("twitch.tv") or url.startswith("www."):
                url = f"https://{url.removeprefix('www.')}"

            pre_tier = resolve_tier(source_kind=kind, url=url)
            cached_meta = download_url(
                url, self.cfg, tier=pre_tier, on_progress=on_progress,
            )
            self._materialize_to_workspace(cached_meta.path, local_path)
            meta = VideoMeta(**{**vars(cached_meta), "path": local_path, "url": url})

            # Durable copy in job prefix (async-safe; single upload)
            storage_key = job_key(request.job_id, "source", CANONICAL_SOURCE_NAME)
            if not self.storage.exists(storage_key):
                self.storage.upload(storage_key, local_path, content_type="video/mp4")

        else:
            assert request.local_path
            meta = resolve_local(Path(request.local_path), local_path, self.cfg)
            storage_key = job_key(request.job_id, "source", CANONICAL_SOURCE_NAME)
            if not self.storage.exists(storage_key):
                self.storage.upload(storage_key, local_path, content_type="video/mp4")

        tier = resolve_tier(
            source_kind=kind,
            url=request.source_url,
            duration_secs=meta.duration,
        )
        hints = self._pipeline_hints(tier)

        log.info(
            "ingest_complete",
            job_id=request.job_id,
            kind=kind.value,
            tier=tier.value,
            duration_secs=meta.duration,
            storage_key=storage_key,
        )

        return IngestResult(
            meta=meta,
            local_path=local_path,
            source_kind=kind,
            processing_tier=tier,
            storage_key=storage_key,
            pipeline_hints=hints,
        )

    @staticmethod
    def _materialize_to_workspace(src: Path, dest: Path) -> None:
        """Copy cached download into job workspace (hardlink if same volume)."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            return
        try:
            src.link(dest)  # hardlink when possible
        except OSError:
            shutil.copy2(src, dest)

    def _pipeline_hints(self, tier) -> dict:
        from core.ingest.types import ProcessingTier

        hints: dict = {"skip_optical_flow": False}
        if tier == ProcessingTier.SHORT:
            hints["skip_optical_flow"] = self.cfg.ingest.short_skip_optical_flow
            hints["min_clip_duration_override"] = self.cfg.ingest.short_min_clip_duration
        elif tier == ProcessingTier.MEDIUM:
            hints["skip_optical_flow"] = self.cfg.ingest.medium_skip_optical_flow
        return hints


def get_job_source_path(cfg: Settings, job_id: str) -> Path:
    """Canonical local source path for a job (used by downstream tasks)."""
    return cfg.workspace_dir / "jobs" / job_id / CANONICAL_SOURCE_NAME

"""Ingest orchestrator — single entry for all source types."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import structlog

from core.config import Settings
from core.errors import IngestError
from core.ingest.audio_slate import is_audio_only, render_audio_slate
from core.ingest.classifier import resolve_tier
from core.ingest.probe import probe_video
from core.ingest.resolvers.local import resolve_local
from core.ingest.resolvers.storage import download_from_storage
from core.ingest.resolvers.url import download_url
from core.ingest.types import IngestRequest, IngestResult, SourceKind
from core.ingest.url_normalize import normalize_source_url
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
        on_message: Callable[[str], None] | None = None,
    ) -> IngestResult:
        local_path = self._workspace_source(request.job_id)
        kind = request.kind
        defer_upload = self.cfg.ingest.defer_source_upload
        file_size_bytes: int | None = None

        audio_source = False

        if kind == SourceKind.UPLOAD:
            assert request.storage_key
            if on_message:
                on_message("Copying upload from storage")
            try:
                file_size_bytes = self.storage.size(request.storage_key)
            except Exception:
                file_size_bytes = None
            meta = download_from_storage(
                request.storage_key, local_path, self.cfg, self.storage,
                on_progress=on_progress,
            )
            storage_key = request.storage_key
            if file_size_bytes is None and local_path.exists():
                file_size_bytes = local_path.stat().st_size

            # Phase 4 — audio-to-clip: render a slate video around
            # audio-only uploads so downstream stages see normal video.
            if is_audio_only(meta):
                if not self.cfg.features.audio_ingest:
                    raise IngestError(
                        "Audio ingest disabled",
                        user_message="Audio uploads require the audio-to-clip add-on.",
                    )
                audio_source = True
                meta = self._slate_from_audio(request.job_id, local_path, meta, on_message)
                # Archive the rendered slate as the job source so other
                # workers re-download video, not the raw audio upload.
                storage_key = job_key(request.job_id, "source", CANONICAL_SOURCE_NAME)
                if on_message:
                    on_message("Uploading rendered source")
                self.storage.upload(storage_key, local_path, content_type="video/mp4")

        elif kind == SourceKind.URL:
            assert request.source_url
            url = normalize_source_url(request.source_url)

            pre_tier = resolve_tier(source_kind=kind, url=url)
            if on_message:
                on_message("Downloading source")
            cached_meta, was_cache_hit = download_url(
                url, self.cfg, tier=pre_tier, on_progress=on_progress,
            )
            if was_cache_hit and on_message:
                on_message("Using cached download")
            if on_message:
                on_message("Saving to workspace")
            self._materialize_to_workspace(cached_meta.path, local_path)
            meta = VideoMeta(**{**vars(cached_meta), "path": local_path, "url": url})

            storage_key = job_key(request.job_id, "source", CANONICAL_SOURCE_NAME)
            if (
                not defer_upload
                and not self.storage.exists(storage_key)
                and local_path.exists()
            ):
                if on_message:
                    on_message("Uploading archive")
                self.storage.upload(storage_key, local_path, content_type="video/mp4")

        else:
            assert request.local_path
            meta = resolve_local(Path(request.local_path), local_path, self.cfg)
            storage_key = job_key(request.job_id, "source", CANONICAL_SOURCE_NAME)
            if not defer_upload and not self.storage.exists(storage_key):
                self.storage.upload(storage_key, local_path, content_type="video/mp4")

        if on_message:
            on_message("Probing video")

        tier = resolve_tier(
            source_kind=kind,
            url=url if kind == SourceKind.URL else request.source_url,
            duration_secs=meta.duration,
        )
        hints = self._pipeline_hints(tier)
        if audio_source:
            # Slate frames carry no motion — optical flow is pure waste.
            hints["skip_optical_flow"] = True
            hints["audio_source"] = True

        log.info(
            "ingest_complete",
            job_id=request.job_id,
            kind=kind.value,
            tier=tier.value,
            duration_secs=meta.duration,
            storage_key=storage_key,
            defer_upload=defer_upload,
        )

        result = IngestResult(
            meta=meta,
            local_path=local_path,
            source_kind=kind,
            processing_tier=tier,
            storage_key=storage_key,
            pipeline_hints=hints,
            file_size_bytes=file_size_bytes,
        )
        return result

    def _slate_from_audio(
        self,
        job_id: str,
        local_path: Path,
        meta: VideoMeta,
        on_message: Callable[[str], None] | None,
    ) -> VideoMeta:
        """Replace an audio-only source with a rendered slate video in place."""
        if on_message:
            on_message("Rendering audio slate video")
        audio_path = local_path.with_name("source_audio" + (local_path.suffix or ".bin"))
        local_path.rename(audio_path)
        try:
            render_audio_slate(audio_path, local_path, self.cfg)
        except Exception as exc:
            audio_path.rename(local_path)  # restore for debuggability
            raise IngestError(
                f"Audio slate render failed for job {job_id}",
                user_message="Could not convert the audio file into a video source.",
            ) from exc
        finally:
            if local_path.exists() and audio_path.exists():
                audio_path.unlink(missing_ok=True)

        slate_meta = probe_video(local_path)
        return VideoMeta(
            **{
                **vars(slate_meta),
                "title": meta.title,
                "url": meta.url,
            },
        )

    @staticmethod
    def _materialize_to_workspace(src: Path, dest: Path) -> None:
        """Copy cached download into job workspace (hardlink if same volume)."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            return
        try:
            if hasattr(src, "link_to"):
                src.link_to(dest)
            else:
                src.link(dest)  # pragma: no cover — legacy Python
        except (OSError, AttributeError):
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

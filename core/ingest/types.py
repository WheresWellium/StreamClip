"""Ingest domain types — source classification and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from core.models import VideoMeta


class SourceKind(str, Enum):
    """How the media entered the pipeline."""
    URL = "url"
    UPLOAD = "upload"
    LOCAL = "local"


class ProcessingTier(str, Enum):
    """
    Drives download quality and downstream pipeline cost.

    short  — Twitch clips, Shorts, <2 min (fast path)
    medium — Clips up to ~10 min
    long   — Full VODs / long uploads
    """
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


@dataclass(frozen=True)
class IngestRequest:
    """Normalized ingest input regardless of entry point."""
    job_id: str
    source_url: str | None = None
    storage_key: str | None = None
    local_path: Path | None = None

    @property
    def kind(self) -> SourceKind:
        if self.storage_key:
            return SourceKind.UPLOAD
        if self.source_url:
            return SourceKind.URL
        if self.local_path:
            return SourceKind.LOCAL
        raise ValueError("IngestRequest requires url, storage_key, or local_path")


@dataclass
class IngestResult:
    """Canonical output of every ingest resolver."""
    meta: VideoMeta
    local_path: Path
    source_kind: SourceKind
    processing_tier: ProcessingTier
    storage_key: str | None = None
    pipeline_hints: dict[str, Any] = field(default_factory=dict)

    def to_snapshot(self) -> dict[str, Any]:
        """Merge into job config_snapshot for downstream stages."""
        return {
            "source_kind": self.source_kind.value,
            "processing_tier": self.processing_tier.value,
            "source_duration_secs": self.meta.duration,
            **self.pipeline_hints,
        }

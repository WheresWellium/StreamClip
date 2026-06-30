"""Modular ingest package."""

from core.ingest.classifier import classify_duration, classify_url, resolve_tier
from core.ingest.service import IngestService, get_job_source_path
from core.ingest.types import IngestRequest, IngestResult, ProcessingTier, SourceKind

__all__ = [
    "IngestService",
    "IngestRequest",
    "IngestResult",
    "ProcessingTier",
    "SourceKind",
    "classify_duration",
    "classify_url",
    "get_job_source_path",
    "resolve_tier",
]

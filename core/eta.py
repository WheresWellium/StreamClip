"""Duration-based pipeline ETA estimation."""

from __future__ import annotations

from typing import Any

from core.config import Settings

# Canonical pipeline stages in execution order
PIPELINE_STAGES: tuple[str, ...] = (
    "ingest",
    "transcribe",
    "highlights",
    "virality",
    "process_clip",
)

# Map SSE / DB stage strings to canonical ETA stage keys
STAGE_ALIASES: dict[str, str] = {
    "queued": "ingest",
    "ingesting": "ingest",
    "ingested": "ingest",
    "transcribing": "transcribe",
    "transcribed": "transcribe",
    "detecting": "highlights",
    "detected": "highlights",
    "scoring_virality": "virality",
    "processing": "process_clip",
    "rendering": "process_clip",
    "completed": "process_clip",
    "done": "process_clip",
}


def canonical_stage(stage: str) -> str:
    """Normalize a progress stage name to a canonical ETA stage."""
    return STAGE_ALIASES.get(stage, stage)


def is_gpu_profile(cfg: Settings) -> bool:
    device = str(cfg.whisper.device).lower()
    codec = str(cfg.export.codec).lower()
    return device in ("cuda", "auto") or "nvenc" in codec


def processing_profile(cfg: Settings) -> str:
    return "gpu" if is_gpu_profile(cfg) else "cpu"


def estimate_stage_seconds(
    stage: str,
    *,
    duration_secs: float,
    source_kind: str,
    target_clips: int,
    skip_optical_flow: bool,
    cfg: Settings,
    file_size_bytes: int | None = None,
) -> float:
    """Estimate wall seconds for a single pipeline stage."""
    duration = max(duration_secs, 1.0)
    clips = max(target_clips, 1)
    gpu = is_gpu_profile(cfg)

    if stage == "ingest":
        if source_kind == "upload":
            if file_size_bytes and file_size_bytes > 0:
                # Assume ~80 Mbps effective MinIO→worker on Docker LAN
                mbps = 80.0
                return max(15.0, (file_size_bytes * 8) / (mbps * 1_000_000))
            return max(30.0, duration * 0.05)
        return max(30.0, duration * 0.08)

    if stage == "transcribe":
        rtf = 0.3 if gpu else 1.0
        return duration * rtf

    if stage == "highlights":
        base = (duration / 3600.0) * 180.0
        if skip_optical_flow:
            base *= 0.45
        return max(20.0, base)

    if stage == "virality":
        return 30.0

    if stage == "process_clip":
        per_clip = 45.0 if gpu else 90.0
        return per_clip * clips

    return 60.0


def estimate_total_seconds(
    *,
    duration_secs: float,
    source_kind: str,
    target_clips: int,
    skip_optical_flow: bool,
    cfg: Settings,
    file_size_bytes: int | None = None,
) -> float:
    return sum(
        estimate_stage_seconds(
            stage,
            duration_secs=duration_secs,
            source_kind=source_kind,
            target_clips=target_clips,
            skip_optical_flow=skip_optical_flow,
            cfg=cfg,
            file_size_bytes=file_size_bytes,
        )
        for stage in PIPELINE_STAGES
    )


def estimate_remaining_seconds(
    current_stage: str,
    *,
    stage_durations: dict[str, float],
    stage_elapsed_secs: float,
    duration_secs: float | None,
    source_kind: str,
    target_clips: int,
    skip_optical_flow: bool,
    cfg: Settings,
    file_size_bytes: int | None = None,
) -> float | None:
    """
    Estimate seconds until job completion from the current stage onward.
    Returns None when duration is unknown (before ingest completes).
    """
    if duration_secs is None or duration_secs <= 0:
        return None

    current = canonical_stage(current_stage)
    try:
        current_idx = PIPELINE_STAGES.index(current)
    except ValueError:
        current_idx = 0

    remaining = 0.0
    for i, stage in enumerate(PIPELINE_STAGES):
        estimate = estimate_stage_seconds(
            stage,
            duration_secs=duration_secs,
            source_kind=source_kind,
            target_clips=target_clips,
            skip_optical_flow=skip_optical_flow,
            cfg=cfg,
            file_size_bytes=file_size_bytes,
        )
        spent = stage_durations.get(stage, 0.0)
        if i < current_idx:
            continue
        if i == current_idx:
            remaining += max(0.0, estimate - max(spent, stage_elapsed_secs))
        else:
            remaining += max(0.0, estimate - spent)

    return max(0.0, remaining)


def build_eta_context(
    *,
    duration_secs: float,
    source_kind: str,
    target_clips: int,
    skip_optical_flow: bool,
    file_size_bytes: int | None = None,
) -> dict[str, Any]:
    """Serializable context stored in Redis after ingest for ETA updates."""
    return {
        "duration_secs": duration_secs,
        "source_kind": source_kind,
        "target_clips": target_clips,
        "skip_optical_flow": skip_optical_flow,
        "file_size_bytes": file_size_bytes,
    }

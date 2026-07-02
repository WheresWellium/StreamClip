"""ETA estimation unit tests."""

from __future__ import annotations

from core.config import Settings
from core.eta import (
    PIPELINE_STAGES,
    canonical_stage,
    estimate_remaining_seconds,
    estimate_stage_seconds,
    estimate_total_seconds,
    is_gpu_profile,
    processing_profile,
)


def test_canonical_stage_aliases():
    assert canonical_stage("ingesting") == "ingest"
    assert canonical_stage("transcribing") == "transcribe"
    assert canonical_stage("detecting") == "highlights"
    assert canonical_stage("rendering") == "process_clip"


def test_processing_profile_cpu_vs_gpu():
    cpu_cfg = Settings(whisper={"device": "cpu"}, export={"codec": "libx264"})
    gpu_cfg = Settings(whisper={"device": "cuda"}, export={"codec": "h264_nvenc"})
    assert processing_profile(cpu_cfg) == "cpu"
    assert processing_profile(gpu_cfg) == "gpu"
    assert is_gpu_profile(gpu_cfg) is True


def test_estimate_stage_seconds_ingest_url():
    cfg = Settings()
    secs = estimate_stage_seconds(
        "ingest",
        duration_secs=3600,
        source_kind="url",
        target_clips=5,
        skip_optical_flow=False,
        cfg=cfg,
    )
    assert secs >= 30.0
    assert secs == max(30.0, 3600 * 0.08)


def test_estimate_stage_seconds_ingest_upload_by_size():
    cfg = Settings()
    secs = estimate_stage_seconds(
        "ingest",
        duration_secs=600,
        source_kind="upload",
        target_clips=5,
        skip_optical_flow=False,
        cfg=cfg,
        file_size_bytes=500_000_000,
    )
    assert secs >= 15.0


def test_estimate_total_seconds_monotonic_with_duration():
    cfg = Settings()
    short = estimate_total_seconds(
        duration_secs=120,
        source_kind="url",
        target_clips=3,
        skip_optical_flow=True,
        cfg=cfg,
    )
    long = estimate_total_seconds(
        duration_secs=7200,
        source_kind="url",
        target_clips=3,
        skip_optical_flow=True,
        cfg=cfg,
    )
    assert long > short


def test_estimate_remaining_unknown_duration():
    cfg = Settings()
    remaining = estimate_remaining_seconds(
        "ingesting",
        stage_durations={},
        stage_elapsed_secs=10.0,
        duration_secs=None,
        source_kind="url",
        target_clips=5,
        skip_optical_flow=False,
        cfg=cfg,
    )
    assert remaining is None


def test_estimate_remaining_decreases_with_progress():
    cfg = Settings()
    duration = 600.0
    early = estimate_remaining_seconds(
        "transcribe",
        stage_durations={"ingest": 30.0},
        stage_elapsed_secs=5.0,
        duration_secs=duration,
        source_kind="url",
        target_clips=5,
        skip_optical_flow=False,
        cfg=cfg,
    )
    late = estimate_remaining_seconds(
        "transcribe",
        stage_durations={"ingest": 30.0},
        stage_elapsed_secs=500.0,
        duration_secs=duration,
        source_kind="url",
        target_clips=5,
        skip_optical_flow=False,
        cfg=cfg,
    )
    assert early is not None and late is not None
    assert late < early


def test_pipeline_stages_order():
    assert PIPELINE_STAGES[0] == "ingest"
    assert PIPELINE_STAGES[-1] == "process_clip"

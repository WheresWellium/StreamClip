"""
Phase 2b-ii — Source waveform rendering for the timeline editor.

A single ``showwavespic`` pass produces one PNG per job, generated once on
the ingest worker (CPU queue) and cached in object storage. The web editor
uses it as the trim-track background; failure is always non-fatal.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import structlog

from core.config import Settings
from core.ffmpeg_bins import ffmpeg_bin
from core.storage import Storage, job_key

log = structlog.get_logger(__name__)

WAVEFORM_NAME = "waveform.png"
_WAVEFORM_SIZE = "1200x120"
_WAVEFORM_COLOR = "0x38BDF8"  # sky-400, matches the app accent


def waveform_storage_key(job_id: str) -> str:
    return job_key(job_id, "meta", WAVEFORM_NAME)


def render_waveform_png(source_path: Path, output_path: Path) -> Path:
    """Render a mono amplitude waveform image for the full source audio."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_bin(), "-y", "-i", str(source_path),
        "-filter_complex",
        f"aformat=channel_layouts=mono,showwavespic=s={_WAVEFORM_SIZE}:colors={_WAVEFORM_COLOR}",
        "-frames:v", "1",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def ensure_job_waveform(
    job_id: str,
    source_path: Path,
    cfg: Settings,
    storage: Storage,
) -> str | None:
    """
    Idempotently render + upload the job waveform. Returns the storage key,
    or None when generation fails (silent sources, codec issues).
    """
    key = waveform_storage_key(job_id)
    try:
        if storage.exists(key):
            return key
        local = cfg.workspace_dir / "jobs" / job_id / WAVEFORM_NAME
        if not local.exists():
            render_waveform_png(source_path, local)
        storage.upload(key, local, content_type="image/png")
        log.info("waveform_generated", job_id=job_id, key=key)
        return key
    except Exception as exc:  # noqa: BLE001 — cosmetic asset, never fatal
        log.warning("waveform_generation_failed", job_id=job_id, error=str(exc))
        return None

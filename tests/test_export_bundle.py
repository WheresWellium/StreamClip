"""export_bundle tests."""

from __future__ import annotations

import zipfile
from io import BytesIO
from unittest.mock import MagicMock

import pytest

from backend.db.models import Clip, ClipStatus, Job, JobStatus
from core.export_bundle import _safe_filename, build_job_clips_zip


def test_safe_filename():
    assert _safe_filename("Hello World!", 0).endswith(".mp4")
    assert _safe_filename("", 1).startswith("02_")


def test_build_job_clips_zip():
    job = Job(
        id="j1",
        status=JobStatus.DONE,
        current_stage="done",
        progress=1.0,
        config_snapshot={},
    )
    c1 = Clip(
        id="c1",
        job_id="j1",
        rank=0,
        start_secs=0,
        end_secs=1,
        title="Clip",
        status=ClipStatus.DONE,
        final_storage_key="k1",
    )
    job.clips = [c1]
    storage = MagicMock()
    storage.download.side_effect = lambda key, dest: dest.write_bytes(b"mp4")

    data = build_job_clips_zip(job, storage)
    zf = zipfile.ZipFile(BytesIO(data))
    assert zf.namelist()


def test_build_job_clips_zip_empty():
    job = Job(
        id="j1",
        status=JobStatus.DONE,
        current_stage="done",
        progress=1.0,
        config_snapshot={},
    )
    job.clips = []
    with pytest.raises(ValueError):
        build_job_clips_zip(job, MagicMock())

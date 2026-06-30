"""Pipeline task module smoke tests (no heavy ML imports)."""

from __future__ import annotations

from pathlib import Path


def test_pipeline_tasks_imports_storage_helpers():
    src = Path(__file__).resolve().parents[1] / "core" / "tasks" / "pipeline_tasks.py"
    text = src.read_text(encoding="utf-8")
    assert "from core.storage import job_key, make_storage" in text


def test_storage_helpers_callable():
    from core.storage import job_key, make_storage

    assert callable(job_key)
    assert callable(make_storage)
    assert job_key("abc", "source", "source.mp4") == "jobs/abc/source/source.mp4"

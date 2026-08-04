"""Unit tests for create-option pipeline timing matrix summarize rules."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "matrix_create_pipeline_timing.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("matrix_create_pipeline_timing", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def matrix_mod():
    return _load_mod()


def test_summarize_pipeline_green_allows_short_of_target(tmp_path: Path, matrix_mod) -> None:
    keys = ["gaming|16:9|c1", "gaming|16:9|c10"]
    rows = [
        {
            "cell_key": "gaming|16:9|c1",
            "status": "done",
            "target_clips": 1,
            "clip_count": 1,
            "wall_s": 10.0,
        },
        {
            "cell_key": "gaming|16:9|c10",
            "status": "done",
            "target_clips": 10,
            "clip_count": 1,
            "wall_s": 12.0,
        },
    ]
    path = tmp_path / "results.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    summary = matrix_mod.summarize(path, keys, require_target_clips=False)
    assert summary["pipeline_green"] is True
    assert summary["green"] is True
    assert summary["clips_short_of_target"] == 1
    assert summary["target_clips_green"] is False


def test_summarize_require_target_clips_fails_when_short(tmp_path: Path, matrix_mod) -> None:
    keys = ["gaming|16:9|c10"]
    path = tmp_path / "results.jsonl"
    path.write_text(
        json.dumps(
            {
                "cell_key": "gaming|16:9|c10",
                "status": "done",
                "target_clips": 10,
                "clip_count": 1,
                "wall_s": 12.0,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    summary = matrix_mod.summarize(path, keys, require_target_clips=True)
    assert summary["pipeline_green"] is True
    assert summary["green"] is False
    assert summary["clips_short_of_target"] == 1


def test_summarize_done_without_clips_is_not_green(tmp_path: Path, matrix_mod) -> None:
    keys = ["gaming|16:9|c1"]
    path = tmp_path / "results.jsonl"
    path.write_text(
        json.dumps(
            {
                "cell_key": "gaming|16:9|c1",
                "status": "done",
                "target_clips": 1,
                "clip_count": 0,
                "wall_s": 8.0,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    summary = matrix_mod.summarize(path, keys)
    assert summary["done"] == 0
    assert summary["failed"] == 1
    assert summary["green"] is False

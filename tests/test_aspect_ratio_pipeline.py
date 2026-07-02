"""Aspect-ratio propagation through job snapshot and clip overrides."""

from __future__ import annotations

from types import SimpleNamespace

from core.tasks import pipeline_tasks as pt


def test_apply_job_config_sets_dimensions() -> None:
    job = SimpleNamespace(config_snapshot={"aspect_ratio": "1:1"})
    pt._apply_job_config(job)
    assert (pt.cfg.reframe.target_width, pt.cfg.reframe.target_height) == (1080, 1080)


def test_apply_job_config_missing_key_resets_to_default() -> None:
    # Simulate a previous job having set a wide target on the singleton cfg
    pt.cfg.reframe.target_width = 1920
    pt.cfg.reframe.target_height = 1080
    job = SimpleNamespace(config_snapshot={"target_clips": 3})
    pt._apply_job_config(job)
    assert (pt.cfg.reframe.target_width, pt.cfg.reframe.target_height) == (1080, 1920)


def test_apply_clip_override_wins_over_job() -> None:
    job = SimpleNamespace(config_snapshot={"aspect_ratio": "9:16"})
    clip = SimpleNamespace(render_overrides={"aspect_ratio": "16:9"})
    pt._apply_job_config(job)
    pt._apply_clip_overrides(job, clip)
    assert (pt.cfg.reframe.target_width, pt.cfg.reframe.target_height) == (1920, 1080)


def test_invalid_aspect_ratio_ignored() -> None:
    pt.cfg.reframe.target_width = 1080
    pt.cfg.reframe.target_height = 1920
    clip = SimpleNamespace(render_overrides={"aspect_ratio": "13:37"})
    pt._apply_clip_overrides(SimpleNamespace(config_snapshot={}), clip)
    assert (pt.cfg.reframe.target_width, pt.cfg.reframe.target_height) == (1080, 1920)

"""Aspect-ratio propagation through job snapshot and clip overrides."""

from __future__ import annotations

from types import SimpleNamespace

from core.tasks import pipeline_tasks as pt


def test_apply_job_config_sets_dimensions() -> None:
    job = SimpleNamespace(config_snapshot={"aspect_ratio": "1:1"})
    pt._apply_job_config(pt.cfg, job)
    assert (pt.cfg.reframe.target_width, pt.cfg.reframe.target_height) == (1080, 1080)


def test_apply_job_config_missing_key_resets_to_default() -> None:
    # Simulate a previous job having set a wide target on the singleton cfg
    pt.cfg.reframe.target_width = 1920
    pt.cfg.reframe.target_height = 1080
    job = SimpleNamespace(config_snapshot={"target_clips": 3})
    pt._apply_job_config(pt.cfg, job)
    assert (pt.cfg.reframe.target_width, pt.cfg.reframe.target_height) == (1080, 1920)


def test_apply_clip_override_wins_over_job() -> None:
    job = SimpleNamespace(config_snapshot={"aspect_ratio": "9:16"})
    clip = SimpleNamespace(render_overrides={"aspect_ratio": "16:9"})
    pt._apply_job_config(pt.cfg, job)
    pt._apply_clip_overrides(pt.cfg, job, clip)
    assert (pt.cfg.reframe.target_width, pt.cfg.reframe.target_height) == (1920, 1080)


def test_invalid_aspect_ratio_ignored() -> None:
    pt.cfg.reframe.target_width = 1080
    pt.cfg.reframe.target_height = 1920
    clip = SimpleNamespace(render_overrides={"aspect_ratio": "13:37"})
    pt._apply_clip_overrides(pt.cfg, SimpleNamespace(config_snapshot={}), clip)
    assert (pt.cfg.reframe.target_width, pt.cfg.reframe.target_height) == (1080, 1920)


def test_apply_clip_overrides_on_local_copy_does_not_mutate_module_cfg() -> None:
    """Regression test for the process_clip concurrency race (MASTER_TODO #10.6).

    Two "concurrent" clips with different overrides must each render with
    their own settings — neither should see the other's aspect ratio or
    profanity mode, and the shared module-level cfg must stay untouched.
    """
    baseline_width = pt.cfg.reframe.target_width
    baseline_height = pt.cfg.reframe.target_height
    baseline_mode = pt.cfg.caption.profanity_mode

    job = SimpleNamespace(config_snapshot={})
    clip_a = SimpleNamespace(
        render_overrides={"aspect_ratio": "9:16", "profanity_mode": "bleep"},
    )
    clip_b = SimpleNamespace(
        render_overrides={"aspect_ratio": "1:1", "profanity_mode": "omit"},
    )

    local_cfg_a = pt.cfg.model_copy(deep=True)
    local_cfg_b = pt.cfg.model_copy(deep=True)

    # Interleave the two "tasks" the way a Celery group() would run them
    # concurrently on a prefork/gevent worker.
    pt._apply_job_config(local_cfg_a, job)
    pt._apply_job_config(local_cfg_b, job)
    pt._apply_clip_overrides(local_cfg_a, job, clip_a)
    pt._apply_clip_overrides(local_cfg_b, job, clip_b)

    assert (local_cfg_a.reframe.target_width, local_cfg_a.reframe.target_height) == (1080, 1920)
    assert local_cfg_a.caption.profanity_mode == "bleep"

    assert (local_cfg_b.reframe.target_width, local_cfg_b.reframe.target_height) == (1080, 1080)
    assert local_cfg_b.caption.profanity_mode == "omit"

    # The shared module singleton must be untouched by either local copy.
    assert pt.cfg.reframe.target_width == baseline_width
    assert pt.cfg.reframe.target_height == baseline_height
    assert pt.cfg.caption.profanity_mode == baseline_mode

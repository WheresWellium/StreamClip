"""Celery progress publishing tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.celery_app import publish_job_progress, publish_progress
from core.distribution.notify import record_publish_outcome


def test_publish_progress_clamps_values():
    mock_redis = MagicMock()
    mock_redis.incr.return_value = 1
    with patch("core.celery_app.get_redis", return_value=mock_redis):
        publish_progress("job1", stage="ingesting", progress=1.5, message="hi")
    mock_redis.incr.assert_called_once()
    mock_redis.publish.assert_called_once()
    mock_redis.set.assert_called_once()
    args = mock_redis.publish.call_args[0]
    assert args[0].endswith("job1")
    published = __import__("json").loads(args[1])
    assert published["progress"] == 1.0


def test_publish_job_progress_publishes_to_redis():
    mock_redis = MagicMock()
    mock_redis.incr.return_value = 1
    with patch("core.celery_app.get_redis", return_value=mock_redis):
        publish_job_progress("pj-1", stage="upload", progress=0.5, message="Uploading", status="processing")
    mock_redis.publish.assert_called_once()


def test_record_publish_outcome_duration():
    record_publish_outcome(platform="tiktok", status="succeeded", duration_secs=12.5)
    record_publish_outcome(platform="tiktok", status="failed", duration_secs=3.0)

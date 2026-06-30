"""Celery progress publishing tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.celery_app import publish_progress


def test_publish_progress_clamps_values():
    mock_redis = MagicMock()
    with patch("core.celery_app.get_redis", return_value=mock_redis):
        publish_progress("job1", stage="ingesting", progress=1.5, message="hi")
    mock_redis.publish.assert_called_once()
    mock_redis.set.assert_called_once()
    args = mock_redis.publish.call_args[0]
    assert args[0].endswith("job1")

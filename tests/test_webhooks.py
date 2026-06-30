"""Tests for job completion webhooks."""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

from core.config import WebhookConfig
from core.webhooks import _sign_payload, deliver_job_webhook


def test_sign_payload_empty_secret() -> None:
    assert _sign_payload(b"{}", "") == ""


def test_sign_payload_hmac() -> None:
    body = b'{"event":"job.completed"}'
    sig = _sign_payload(body, "test-secret")
    expected = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
    assert sig == f"sha256={expected}"


@patch("core.webhooks.httpx.Client")
def test_deliver_job_webhook_success(mock_client_cls: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.status_code = 200
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    cfg = WebhookConfig(enabled=True, url="https://example.com/hook", secret="s")
    ok = deliver_job_webhook(
        job_id="job-1",
        status="done",
        done_count=3,
        error_count=0,
        cfg=cfg,
    )
    assert ok is True
    call_kwargs = mock_client.post.call_args
    body = call_kwargs.kwargs.get("content") or call_kwargs.args[1]
    payload = json.loads(body)
    assert payload["job_id"] == "job-1"
    assert payload["clips_done"] == 3


def test_deliver_job_webhook_disabled() -> None:
    cfg = WebhookConfig(enabled=False, url="https://example.com/hook")
    assert deliver_job_webhook(
        job_id="x", status="done", done_count=1, error_count=0, cfg=cfg,
    ) is False

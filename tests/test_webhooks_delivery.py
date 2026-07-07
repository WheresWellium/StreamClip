"""Outbound webhook delivery helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx

from core.config import WebhookConfig
from core.webhooks import (
    _sign_payload,
    deliver_clip_webhook,
    deliver_job_webhook,
    deliver_publish_webhook,
    deliver_webhook,
)


def test_sign_payload_empty_secret():
    assert _sign_payload(b"{}", "") == ""


def test_deliver_webhook_empty_url():
    assert deliver_webhook(event="x", url="  ", secret="s", payload={}) is False


def test_deliver_webhook_success():
    resp = MagicMock(is_success=True, status_code=200)
    client = MagicMock()
    client.post.return_value = resp
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)

    with patch("core.webhooks.httpx.Client", return_value=client):
        ok = deliver_webhook(
            event="job.completed",
            url="https://hook.example.com",
            secret="secret",
            payload={"job_id": "j1"},
            max_retries=1,
        )
    assert ok is True
    assert "X-StreamClip-Signature" in client.post.call_args.kwargs["headers"]


def test_deliver_webhook_retries_on_http_error():
    bad = MagicMock(is_success=False, status_code=500)
    client = MagicMock()
    client.post.return_value = bad
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)

    with patch("core.webhooks.httpx.Client", return_value=client), \
         patch("core.webhooks.time.sleep"):
        ok = deliver_webhook(
            event="job.completed",
            url="https://hook.example.com",
            secret="",
            payload={},
            max_retries=2,
        )
    assert ok is False
    assert client.post.call_count == 2


def test_deliver_webhook_network_error():
    client = MagicMock()
    client.post.side_effect = httpx.ConnectError("down")
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)

    with patch("core.webhooks.httpx.Client", return_value=client), \
         patch("core.webhooks.time.sleep"):
        assert deliver_webhook(
            event="x", url="https://x", secret="", payload={}, max_retries=1,
        ) is False


def test_deliver_job_webhook_global_and_user():
    cfg = WebhookConfig(enabled=True, url="https://global", secret="g", timeout_secs=5, max_retries=1)
    with patch("core.webhooks.deliver_webhook", side_effect=[True, True]) as send:
        ok = deliver_job_webhook(
            job_id="j1",
            status="done",
            done_count=3,
            error_count=0,
            cfg=cfg,
            user_webhook_url="https://user",
            user_webhook_secret="u",
            extra={"foo": "bar"},
        )
    assert ok is True
    assert send.call_count == 2


def test_deliver_clip_webhook_events():
    cfg = WebhookConfig(enabled=True, url="https://global", secret="", timeout_secs=5, max_retries=1)
    with patch("core.webhooks.deliver_webhook", return_value=True) as send:
        deliver_clip_webhook(
            job_id="j1",
            clip_id="c1",
            status="done",
            cfg=cfg,
            extra={"rank": 1},
        )
    assert send.call_args.kwargs["event"] == "clip.rendered"

    with patch("core.webhooks.deliver_webhook", return_value=True) as send:
        deliver_clip_webhook(job_id="j1", clip_id="c1", status="error", cfg=cfg)
    assert send.call_args.kwargs["event"] == "clip.failed"


def test_deliver_clip_webhook_user_url():
    cfg = WebhookConfig(enabled=False, url="", secret="", timeout_secs=5, max_retries=1)
    with patch("core.webhooks.deliver_webhook", return_value=True) as send:
        ok = deliver_clip_webhook(
            job_id="j1",
            clip_id="c1",
            status="done",
            cfg=cfg,
            user_webhook_url="https://user-hook",
            user_webhook_secret="sec",
        )
    assert ok is True
    assert send.call_args.kwargs["url"] == "https://user-hook"


def test_deliver_publish_webhook_optional_fields():
    cfg = WebhookConfig(enabled=False, url="", secret="", timeout_secs=5, max_retries=1)
    with patch("core.webhooks.deliver_webhook", return_value=True) as send:
        deliver_publish_webhook(
            event="publish.published",
            publish_job_id="pj-1",
            platform="youtube_shorts",
            status="published",
            cfg=cfg,
            clip_id="c1",
            vault_clip_id="vc-1",
            external_url="https://yt",
            error_message="none",
            scheduled_at="2026-01-01T00:00:00Z",
            extra={"k": "v"},
            user_webhook_url="https://user",
        )
    payload = send.call_args.kwargs["payload"]
    assert payload["clip_id"] == "c1"
    assert payload["external_url"] == "https://yt"

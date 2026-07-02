"""Tests for publish lifecycle webhooks and metrics."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.db.models import User, VaultClip
from core.config import WebhookConfig
from core.distribution.notify import notify_publish_event, record_publish_outcome
from core.webhooks import deliver_publish_webhook


def test_deliver_publish_webhook_includes_ids() -> None:
    with patch("core.webhooks.deliver_webhook", return_value=True) as mock_deliver:
        ok = deliver_publish_webhook(
            event="publish.published",
            publish_job_id="pj-1",
            platform="youtube_shorts",
            status="published",
            cfg=WebhookConfig(enabled=True, url="https://example.com/hook", secret="s"),
            clip_id="clip-1",
            external_url="https://youtube.com/watch?v=abc",
        )
    assert ok is True
    mock_deliver.assert_called_once()
    assert mock_deliver.call_args.kwargs["event"] == "publish.published"
    payload = mock_deliver.call_args.kwargs["payload"]
    assert payload["publish_job_id"] == "pj-1"
    assert payload["clip_id"] == "clip-1"
    assert payload["external_url"] == "https://youtube.com/watch?v=abc"


@patch("core.webhooks.httpx.Client")
def test_deliver_publish_webhook_http(mock_client_cls: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.status_code = 200
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    cfg = WebhookConfig(enabled=True, url="https://example.com/hook", secret="s")
    ok = deliver_publish_webhook(
        event="publish.failed",
        publish_job_id="pj-2",
        platform="tiktok",
        status="failed",
        cfg=cfg,
        vault_clip_id="vault-1",
        error_message="Platform rejected",
    )
    assert ok is True
    body = mock_client.post.call_args.kwargs.get("content") or mock_client.post.call_args.args[1]
    payload = json.loads(body)
    assert payload["event"] == "publish.failed"
    assert payload["vault_clip_id"] == "vault-1"


@pytest.mark.asyncio
async def test_notify_publish_event_resolves_vault_owner() -> None:
    job = MagicMock()
    job.id = "pj-3"
    job.platform = "youtube_shorts"
    job.status = "published"
    job.clip_id = None
    job.vault_clip_id = "vault-9"
    job.external_url = "https://youtu.be/x"
    job.error_message = None
    job.scheduled_at = None

    vault = MagicMock()
    vault.user_id = "user-1"
    user = MagicMock()
    user.webhook_url = "https://user.example/hook"
    user.webhook_secret = "secret"

    db = AsyncMock()

    async def fake_get(model, pk):  # noqa: ARG001
        if model is VaultClip:
            return vault
        if model is User:
            return user
        return None

    db.get = AsyncMock(side_effect=fake_get)

    with patch("core.distribution.notify.deliver_publish_webhook", return_value=True) as mock_hook:
        await notify_publish_event(db, job, event="publish.published")

    mock_hook.assert_called_once()
    assert mock_hook.call_args.kwargs["user_webhook_url"] == "https://user.example/hook"


def test_record_publish_outcome_increments_counter() -> None:
    before = (
        __import__("prometheus_client").REGISTRY.get_sample_value(
            "streamclip_publish_jobs_total",
            {"status": "started", "platform": "youtube_shorts"},
        )
        or 0.0
    )
    record_publish_outcome(platform="youtube_shorts", status="started")
    after = __import__("prometheus_client").REGISTRY.get_sample_value(
        "streamclip_publish_jobs_total",
        {"status": "started", "platform": "youtube_shorts"},
    )
    assert after == before + 1.0

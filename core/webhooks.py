"""Outbound webhooks for job and clip lifecycle events."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import httpx
import structlog

from core.config import WebhookConfig

log = structlog.get_logger(__name__)


def _sign_payload(body: bytes, secret: str) -> str:
    if not secret:
        return ""
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def deliver_webhook(
    *,
    event: str,
    url: str,
    secret: str,
    payload: dict[str, Any],
    timeout_secs: float = 10.0,
    max_retries: int = 3,
) -> bool:
    """POST a signed JSON payload. Returns True on HTTP 2xx."""
    if not url.strip():
        return False

    body_payload = {"event": event, "ts": time.time(), **payload}
    body = json.dumps(body_payload, separators=(",", ":")).encode()
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "qClip-Webhook/1.0",
    }
    signature = _sign_payload(body, secret)
    if signature:
        headers["X-qClip-Signature"] = signature

    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=timeout_secs) as client:
                resp = client.post(url, content=body, headers=headers)
            if resp.is_success:
                log.info("webhook_delivered", webhook_event=event, status=resp.status_code)
                return True
            log.warning(
                "webhook_http_error",
                webhook_event=event,
                status=resp.status_code,
                attempt=attempt + 1,
            )
        except httpx.HTTPError as exc:
            log.warning(
                "webhook_delivery_failed",
                webhook_event=event,
                attempt=attempt + 1,
                error=str(exc),
            )
        time.sleep(1.5 ** attempt)

    return False


def deliver_job_webhook(
    *,
    job_id: str,
    status: str,
    done_count: int,
    error_count: int,
    cfg: WebhookConfig,
    extra: dict[str, Any] | None = None,
    user_webhook_url: str | None = None,
    user_webhook_secret: str | None = None,
) -> bool:
    """Job completion webhook — global config and/or per-user URL."""
    payload: dict[str, Any] = {
        "job_id": job_id,
        "status": status,
        "clips_done": done_count,
        "clips_failed": error_count,
    }
    if extra:
        payload.update(extra)

    delivered = False
    if cfg.enabled and cfg.url.strip():
        delivered = deliver_webhook(
            event="job.completed",
            url=cfg.url,
            secret=cfg.secret,
            payload=payload,
            timeout_secs=cfg.timeout_secs,
            max_retries=cfg.max_retries,
        ) or delivered

    if user_webhook_url:
        delivered = deliver_webhook(
            event="job.completed",
            url=user_webhook_url,
            secret=user_webhook_secret or "",
            payload=payload,
            timeout_secs=cfg.timeout_secs,
            max_retries=cfg.max_retries,
        ) or delivered

    return delivered


def deliver_clip_webhook(
    *,
    job_id: str,
    clip_id: str,
    status: str,
    cfg: WebhookConfig,
    extra: dict[str, Any] | None = None,
    user_webhook_url: str | None = None,
    user_webhook_secret: str | None = None,
) -> bool:
    """Per-clip render webhook."""
    payload: dict[str, Any] = {
        "job_id": job_id,
        "clip_id": clip_id,
        "status": status,
    }
    if extra:
        payload.update(extra)

    delivered = False
    if cfg.enabled and cfg.url.strip():
        delivered = deliver_webhook(
            event="clip.rendered" if status == "done" else "clip.failed",
            url=cfg.url,
            secret=cfg.secret,
            payload=payload,
            timeout_secs=cfg.timeout_secs,
            max_retries=cfg.max_retries,
        ) or delivered

    if user_webhook_url:
        delivered = deliver_webhook(
            event="clip.rendered" if status == "done" else "clip.failed",
            url=user_webhook_url,
            secret=user_webhook_secret or "",
            payload=payload,
            timeout_secs=cfg.timeout_secs,
            max_retries=cfg.max_retries,
        ) or delivered

    return delivered


def deliver_publish_webhook(
    *,
    event: str,
    publish_job_id: str,
    platform: str,
    status: str,
    cfg: WebhookConfig,
    clip_id: str | None = None,
    vault_clip_id: str | None = None,
    external_url: str | None = None,
    error_message: str | None = None,
    scheduled_at: str | None = None,
    extra: dict[str, Any] | None = None,
    user_webhook_url: str | None = None,
    user_webhook_secret: str | None = None,
) -> bool:
    """Publish lifecycle webhook — global config and/or per-user URL."""
    payload: dict[str, Any] = {
        "publish_job_id": publish_job_id,
        "platform": platform,
        "status": status,
    }
    if clip_id:
        payload["clip_id"] = clip_id
    if vault_clip_id:
        payload["vault_clip_id"] = vault_clip_id
    if external_url:
        payload["external_url"] = external_url
    if error_message:
        payload["error_message"] = error_message
    if scheduled_at:
        payload["scheduled_at"] = scheduled_at
    if extra:
        payload.update(extra)

    delivered = False
    if cfg.enabled and cfg.url.strip():
        delivered = deliver_webhook(
            event=event,
            url=cfg.url,
            secret=cfg.secret,
            payload=payload,
            timeout_secs=cfg.timeout_secs,
            max_retries=cfg.max_retries,
        ) or delivered

    if user_webhook_url:
        delivered = deliver_webhook(
            event=event,
            url=user_webhook_url,
            secret=user_webhook_secret or "",
            payload=payload,
            timeout_secs=cfg.timeout_secs,
            max_retries=cfg.max_retries,
        ) or delivered

    return delivered

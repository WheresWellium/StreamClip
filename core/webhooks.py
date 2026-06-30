"""Outbound webhooks when jobs reach a terminal state."""

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


def deliver_job_webhook(
    *,
    job_id: str,
    status: str,
    done_count: int,
    error_count: int,
    cfg: WebhookConfig,
    extra: dict[str, Any] | None = None,
) -> bool:
    """
    POST a signed JSON payload to ``cfg.url``. Returns True on HTTP 2xx.

  Payload schema::

      {
        "event": "job.completed",
        "job_id": "...",
        "status": "done" | "error",
        "clips_done": 3,
        "clips_failed": 0,
        "ts": 1719667200.0
      }
    """
    if not cfg.enabled or not cfg.url.strip():
        return False

    payload: dict[str, Any] = {
        "event": "job.completed",
        "job_id": job_id,
        "status": status,
        "clips_done": done_count,
        "clips_failed": error_count,
        "ts": time.time(),
    }
    if extra:
        payload.update(extra)

    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "StreamClip-Webhook/1.0",
    }
    signature = _sign_payload(body, cfg.secret)
    if signature:
        headers["X-StreamClip-Signature"] = signature

    for attempt in range(cfg.max_retries):
        try:
            with httpx.Client(timeout=cfg.timeout_secs) as client:
                resp = client.post(cfg.url, content=body, headers=headers)
            if resp.is_success:
                log.info("webhook_delivered", job_id=job_id, status=resp.status_code)
                return True
            log.warning(
                "webhook_http_error",
                job_id=job_id,
                status=resp.status_code,
                attempt=attempt + 1,
            )
        except httpx.HTTPError as exc:
            log.warning("webhook_delivery_failed", job_id=job_id, attempt=attempt + 1, error=str(exc))
        time.sleep(1.5 ** attempt)

    return False

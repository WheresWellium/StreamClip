"""
qClip — operator ops webhook (autonomous alerting)

Configure via environment (never commit the URL):

  OPS_WEBHOOK_URL — HTTPS endpoint that accepts JSON POSTs
                    (Discord/Slack incoming webhook, Zapier Catch Hook,
                     custom agent inbox, etc.)

Legacy alias (deprecated, still read for one release):
  N8N_OPS_WEBHOOK_URL

This module does **not** depend on n8n. Route destinations (email, Slack,
agent MCP, etc.) live in whatever receives the webhook.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

import structlog

log = structlog.get_logger(__name__)


def ops_webhook_url() -> str:
    primary = os.environ.get("OPS_WEBHOOK_URL", "").strip()
    if primary:
        return primary
    # One-release compat for installs that still set the old env name.
    return os.environ.get("N8N_OPS_WEBHOOK_URL", "").strip()


def ops_webhook_status() -> str:
    if not ops_webhook_url():
        return "skipped_unconfigured"
    return "queued"


def post_ops_webhook(payload: dict[str, object], *, max_retries: int = 3) -> bool:
    """POST JSON to the configured ops webhook. Returns True on success."""
    url = ops_webhook_url()
    if not url:
        log.info("ops_webhook_skipped_unconfigured", ops_event=payload.get("event"))
        return False

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "qClip-Ops/1.0"},
        method="POST",
    )

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if 200 <= resp.status < 300:
                    log.info("ops_webhook_sent", ops_event=payload.get("event"))
                    return True
                log.warning(
                    "ops_webhook_bad_status",
                    status=resp.status,
                    ops_event=payload.get("event"),
                )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            log.warning(
                "ops_webhook_failed",
                attempt=attempt + 1,
                error=str(exc),
                ops_event=payload.get("event"),
            )
            time.sleep(1.5 ** attempt)
    return False

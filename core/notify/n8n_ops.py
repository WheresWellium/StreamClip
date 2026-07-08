"""
StreamClip — n8n ops webhook (bug reports, beta feedback)

Configure via environment (never commit the webhook URL or destination inbox):

  N8N_OPS_WEBHOOK_URL — n8n Webhook trigger URL (secret path acts as auth)

The Outlook / studio inbox is configured only inside n8n — not in this repo.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

import structlog

log = structlog.get_logger(__name__)


def n8n_ops_webhook_url() -> str:
    return os.environ.get("N8N_OPS_WEBHOOK_URL", "").strip()


def ops_webhook_status() -> str:
    if not n8n_ops_webhook_url():
        return "skipped_unconfigured"
    return "queued"


def post_ops_webhook(payload: dict[str, object], *, max_retries: int = 3) -> bool:
    """POST JSON to the configured n8n webhook. Returns True on success."""
    url = n8n_ops_webhook_url()
    if not url:
        log.info("n8n_ops_webhook_skipped_unconfigured", ops_event=payload.get("event"))
        return False

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if 200 <= resp.status < 300:
                    log.info("n8n_ops_webhook_sent", ops_event=payload.get("event"))
                    return True
                log.warning(
                    "n8n_ops_webhook_bad_status",
                    status=resp.status,
                    ops_event=payload.get("event"),
                )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            log.warning(
                "n8n_ops_webhook_failed",
                attempt=attempt + 1,
                error=str(exc),
                ops_event=payload.get("event"),
            )
            time.sleep(1.5 ** attempt)
    return False

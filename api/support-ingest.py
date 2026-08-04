"""
Hosted support collector (F13) — Vercel serverless on the henna project.

Desktop sidecars POST OPS_WEBHOOK payloads here. Delivery preference:

1. GitHub Issues (+ optional Project) via SUPPORT_GITHUB_TOKEN
2. Optional SMTP email if SMTP_* / BUG_REPORT_TO are still set

Deployed as https://streamclip-henna.vercel.app/api/support-ingest
"""

from __future__ import annotations

import hashlib
import json
import os
import smtplib
import sys
import threading
import time
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# Vercel may load this file with api/ on sys.path or as project-root relative.
_API_DIR = Path(__file__).resolve().parent
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

from support_github import (  # noqa: E402
    file_support_to_github,
    github_project_number,
    github_token,
)

# Short in-memory debounce so rapid identical posts don't spam GitHub/SMTP.
_DEBOUNCE_LOCK = threading.Lock()
_RECENT: dict[str, float] = {}
_DEBOUNCE_SECS = 45.0

_SUPPORT_EVENTS = frozenset({"bug_report", "beta_feedback"})


def _debounce_key(payload: dict) -> str:
    device = str(payload.get("device_id") or "")
    msg = str(payload.get("message") or "").strip()
    event = str(payload.get("event") or "support")
    report_id = str(payload.get("id") or "")
    raw = f"{event}|{device}|{report_id}|{msg}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


def _should_skip_duplicate(payload: dict) -> bool:
    key = _debounce_key(payload)
    now = time.time()
    with _DEBOUNCE_LOCK:
        stale = [k for k, ts in _RECENT.items() if now - ts > _DEBOUNCE_SECS]
        for k in stale:
            _RECENT.pop(k, None)
        if key in _RECENT and (now - _RECENT[key]) < _DEBOUNCE_SECS:
            return True
        _RECENT[key] = now
        return False


def _smtp_send(to: str, subject: str, body: str) -> bool:
    host = os.environ.get("SMTP_HOST", "").strip()
    if not host or not to:
        return False
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    sender = os.environ.get("SMTP_FROM", "streamclip@localhost")
    starttls = os.environ.get("SMTP_STARTTLS", "true").lower() != "false"

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    for attempt in range(3):
        try:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                if starttls:
                    smtp.starttls()
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
            return True
        except Exception:
            time.sleep(1.5 ** attempt)
    return False


def _email_fallback(payload: dict) -> dict:
    event = str(payload.get("event") or "support")
    severity = str(payload.get("severity") or "medium")
    message = str(payload.get("message") or "").strip()
    categories = payload.get("categories") or []
    if isinstance(categories, list):
        cat_s = ", ".join(str(c) for c in categories) or "uncategorized"
    else:
        cat_s = str(categories)

    recipient = os.environ.get("BUG_REPORT_TO", "").strip()
    if not recipient or not os.environ.get("SMTP_HOST", "").strip():
        return {"ok": False, "error": "email_unconfigured"}

    subject = f"[qClip] {event} ({severity}): {cat_s}"
    body_lines = [
        f"event: {event}",
        f"id: {payload.get('id')}",
        f"severity: {severity}",
        f"categories: {cat_s}",
        f"user_id: {payload.get('user_id')}",
        f"device_id: {payload.get('device_id')}",
        f"job_id: {payload.get('job_id')}",
        f"created_at: {payload.get('created_at')}",
        "",
        "message:",
        message or "(empty)",
        "",
        "environment:",
        json.dumps(payload.get("environment") or {}, indent=2),
    ]
    ok = _smtp_send(recipient, subject, "\n".join(body_lines) + "\n")
    if not ok:
        return {"ok": False, "error": "email_failed"}
    return {"ok": True, "delivered": "email"}


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    raw = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(raw)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    if status != 204:
        handler.wfile.write(raw)


class handler(BaseHTTPRequestHandler):  # noqa: N801 — Vercel Python convention
    def do_OPTIONS(self) -> None:  # noqa: N802
        _json_response(self, 204, {})

    def do_GET(self) -> None:  # noqa: N802
        _json_response(
            self,
            200,
            {
                "ok": True,
                "service": "qclip-support-ingest",
                "github_configured": bool(github_token()),
                "project_configured": github_project_number() is not None,
                "project_number": github_project_number(),
                "smtp_configured": bool(
                    os.environ.get("SMTP_HOST", "").strip()
                    and os.environ.get("BUG_REPORT_TO", "").strip()
                ),
            },
        )

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0 or length > 256_000:
            _json_response(self, 400, {"ok": False, "error": "invalid_body"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            _json_response(self, 400, {"ok": False, "error": "invalid_json"})
            return
        if not isinstance(payload, dict):
            _json_response(self, 400, {"ok": False, "error": "expected_object"})
            return

        if _should_skip_duplicate(payload):
            _json_response(
                self,
                200,
                {"ok": True, "delivered": "deduped", "note": "duplicate_suppressed"},
            )
            return

        event = str(payload.get("event") or "support")
        github_error = None

        # In-app bug / feedback → GitHub Issues (+ Project when configured).
        if event in _SUPPORT_EVENTS and github_token():
            result = file_support_to_github(payload)
            if result.get("ok"):
                email_note = None
                if os.environ.get("SUPPORT_ALSO_EMAIL", "").strip().lower() in {
                    "1",
                    "true",
                    "yes",
                }:
                    email_note = _email_fallback(payload)
                _json_response(
                    self,
                    200,
                    {
                        "ok": True,
                        "delivered": "github_issue",
                        "issue_number": result.get("issue_number"),
                        "issue_url": result.get("issue_url"),
                        "project": result.get("project"),
                        "email": email_note,
                    },
                )
                return
            github_error = result.get("error") or "github_issue_failed"

        email = _email_fallback(payload)
        if email.get("ok"):
            _json_response(
                self,
                200,
                {
                    **email,
                    "github_error": github_error,
                },
            )
            return

        if event in _SUPPORT_EVENTS:
            _json_response(
                self,
                503,
                {
                    "ok": False,
                    "error": "support_unconfigured",
                    "hint": (
                        "Set SUPPORT_GITHUB_TOKEN on the Vercel henna project "
                        "(contents: write Issues; project scope to auto-add to a board). "
                        "Optional SMTP fallback: SMTP_* + BUG_REPORT_TO."
                    ),
                    "github_error": github_error or "github_token_unconfigured",
                },
            )
            return

        # Non-support ops events (job_failed / stack_degraded): email-only.
        _json_response(
            self,
            503,
            {
                "ok": False,
                "error": "email_unconfigured",
                "hint": "Set SMTP_* + BUG_REPORT_TO for ops email alerts",
            },
        )

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

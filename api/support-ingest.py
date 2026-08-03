"""
Hosted support collector (F13) — Vercel serverless on the henna project.

Desktop sidecars POST OPS_WEBHOOK payloads here; this forwards to operator email
via SMTP_* / BUG_REPORT_TO env vars on Vercel (secrets stay server-side).

Deployed as https://streamclip-henna.vercel.app/api/support-ingest
"""

from __future__ import annotations

import json
import os
import smtplib
import time
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler


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


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    raw = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(raw)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(raw)


class handler(BaseHTTPRequestHandler):  # noqa: N801 — Vercel Python convention
    def do_OPTIONS(self) -> None:  # noqa: N802
        _json_response(self, 204, {})

    def do_GET(self) -> None:  # noqa: N802
        _json_response(self, 200, {"ok": True, "service": "qclip-support-ingest"})

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

        event = str(payload.get("event") or "support")
        severity = str(payload.get("severity") or "medium")
        message = str(payload.get("message") or "").strip()
        categories = payload.get("categories") or []
        if isinstance(categories, list):
            cat_s = ", ".join(str(c) for c in categories) or "uncategorized"
        else:
            cat_s = str(categories)

        recipient = os.environ.get("BUG_REPORT_TO", "").strip()
        if not recipient:
            _json_response(self, 503, {"ok": False, "error": "recipient_unconfigured"})
            return
        if not os.environ.get("SMTP_HOST", "").strip():
            _json_response(self, 503, {"ok": False, "error": "smtp_unconfigured"})
            return

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
            _json_response(self, 502, {"ok": False, "error": "email_failed"})
            return
        _json_response(self, 200, {"ok": True, "delivered": "email"})

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

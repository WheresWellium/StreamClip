"""Ops event delivery: webhook first, SMTP email fallback, skip when neither."""

from __future__ import annotations

import pytest

from core.notify import ops_webhook


@pytest.fixture(autouse=True)
def _clear_channels(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "OPS_WEBHOOK_URL",
        "N8N_OPS_WEBHOOK_URL",
        "SMTP_HOST",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "BUG_REPORT_TO",
    ):
        monkeypatch.delenv(name, raising=False)


def test_prefers_webhook_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPS_WEBHOOK_URL", "https://hook.example/ops")
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        ops_webhook,
        "post_ops_webhook",
        lambda payload, **_: calls.append(payload) or True,
    )

    assert ops_webhook.deliver_ops_event({"event": "job_failed"}) == "sent"
    assert calls == [{"event": "job_failed"}]


def test_webhook_failure_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPS_WEBHOOK_URL", "https://hook.example/ops")
    monkeypatch.setattr(ops_webhook, "post_ops_webhook", lambda payload, **_: False)

    assert ops_webhook.deliver_ops_event({"event": "stack_degraded"}) == "failed"


def test_falls_back_to_email_without_webhook(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("BUG_REPORT_TO", "ops@example.com")
    sent: list[dict[str, str]] = []

    def fake_send_email(*, to: str, subject: str, body: str, **_: object) -> bool:
        sent.append({"to": to, "subject": subject, "body": body})
        return True

    monkeypatch.setattr("core.notify.email.send_email", fake_send_email)

    status = ops_webhook.deliver_ops_event({"event": "job_failed", "job_id": "j1"})

    assert status == "emailed"
    assert sent[0]["to"] == "ops@example.com"
    assert "job_failed" in sent[0]["subject"]
    assert "j1" in sent[0]["body"]


def test_email_failure_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("BUG_REPORT_TO", "ops@example.com")
    monkeypatch.setattr("core.notify.email.send_email", lambda **_: False)

    assert ops_webhook.deliver_ops_event({"event": "job_failed"}) == "failed"


def test_skips_when_no_channel_configured() -> None:
    assert ops_webhook.deliver_ops_event({"event": "job_failed"}) == "skipped"


def test_skips_when_smtp_host_without_recipient(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")

    assert ops_webhook.deliver_ops_event({"event": "job_failed"}) == "skipped"

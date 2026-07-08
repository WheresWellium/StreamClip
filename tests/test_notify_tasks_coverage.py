"""Coverage for core.tasks.notify_tasks (Phase 3 email + training export)."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.notify.email import SMTPSettings, bug_report_recipient, send_email, smtp_settings_from_env
from core.tasks import notify_tasks as nt


def test_send_bug_report_email_missing_row():
    with patch.object(nt, "_safe_async", return_value=None):
        out = nt.send_bug_report_email("missing-id")
    assert out == {"status": "skipped", "reason": "not_found"}


def test_send_bug_report_email_loads_from_db():
    report = SimpleNamespace(
        id="r1",
        severity="high",
        categories=["captions"],
        user_id="u1",
        device_id="dev",
        job_id="j1",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        message="Captions drift",
        environment={"browser": "pytest"},
    )

    @asynccontextmanager
    async def fake_db_session():
        db = AsyncMock()
        db.get = AsyncMock(return_value=report)
        yield db

    with patch.object(nt, "db_session", fake_db_session), \
         patch.object(nt, "bug_report_recipient", return_value="bugs@test.local"), \
         patch.object(nt, "send_email", return_value=True):
        out = nt.send_bug_report_email("r1")

    assert out["status"] == "sent"


def test_send_bug_report_email_sends():
    report = SimpleNamespace(
        id="r1",
        severity="high",
        categories=["captions", "ui"],
        user_id="u1",
        device_id="dev",
        job_id="j1",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        message="Captions drift",
        environment={"browser": "pytest"},
    )
    with patch.object(nt, "_safe_async", return_value=report), \
         patch.object(nt, "bug_report_recipient", return_value="bugs@test.local"), \
         patch.object(nt, "send_email", return_value=True) as send:
        out = nt.send_bug_report_email("r1")

    assert out["status"] == "sent"
    send.assert_called_once()
    assert "Captions drift" in send.call_args.kwargs["body"]


def test_send_bug_report_email_skipped_when_smtp_off():
    report = SimpleNamespace(
        id="r2",
        severity="low",
        categories=[],
        user_id=None,
        device_id=None,
        job_id=None,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        message="Minor UI glitch",
        environment={},
    )
    with patch.object(nt, "_safe_async", return_value=report), \
         patch.object(nt, "bug_report_recipient", return_value="bugs@test.local"), \
         patch.object(nt, "send_email", return_value=False):
        out = nt.send_bug_report_email("r2")
    assert out["status"] == "skipped"


def test_send_license_key_email_sent():
    with patch.object(nt, "send_email", return_value=True) as send:
        out = nt.send_license_key_email("buyer@test.local", "KEY-ABC", "ord-1")
    assert out["status"] == "sent"
    assert "KEY-ABC" in send.call_args.kwargs["body"]


def test_send_license_key_email_without_order_id():
    with patch.object(nt, "send_email", return_value=False):
        out = nt.send_license_key_email("buyer@test.local", "KEY-XYZ", None)
    assert out["status"] == "skipped"
    assert out["order_id"] == ""


def test_send_password_reset_email_sent():
    reset_url = "https://clip.example.com/reset-password?token=abc"
    with patch.object(nt, "send_email", return_value=True) as send:
        out = nt.send_password_reset_email("user@test.local", reset_url)
    assert out["status"] == "sent"
    assert out["recipient"] == "user@test.local"
    assert reset_url in send.call_args.kwargs["body"]


def test_send_password_reset_email_skipped_when_smtp_off():
    with patch.object(nt, "send_email", return_value=False):
        out = nt.send_password_reset_email("user@test.local", "https://x/reset")
    assert out["status"] == "skipped"


def test_export_training_bundle_skipped_when_no_opt_in():
    with patch.object(nt, "_safe_async", return_value=None):
        out = nt.export_training_bundle("job-x")
    assert out == {"status": "skipped", "job_id": "job-x"}


def test_export_training_bundle_skipped_when_owner_not_opted_in():
    job = SimpleNamespace(id="job-1", owner_id="u1")
    user = SimpleNamespace(data_contribution_opt_in=False)

    @asynccontextmanager
    async def fake_db_session():
        db = AsyncMock()

        async def get(model, pk):
            if pk == "job-1":
                return job
            if pk == "u1":
                return user
            return None

        db.get = AsyncMock(side_effect=get)
        yield db

    with patch.object(nt, "db_session", fake_db_session):
        out = nt.export_training_bundle("job-1")

    assert out == {"status": "skipped", "job_id": "job-1"}


def test_export_training_bundle_uploads_json(tmp_path):
    bundle = {
        "job_id": "job-1",
        "created_at": "2026-01-01T00:00:00+00:00",
        "source_duration_secs": 120.0,
        "config": {"target_clips": 5},
        "clips": [{"rank": 0, "start_secs": 1.0, "end_secs": 10.0}],
    }
    storage = MagicMock()
    uploaded: dict[str, object] = {}

    def capture_upload(key: str, local: Path, **kwargs) -> None:
        uploaded["key"] = key
        uploaded["body"] = local.read_text(encoding="utf-8")

    storage.upload.side_effect = capture_upload

    with patch.object(nt, "_safe_async", return_value=bundle), \
         patch.object(nt, "make_storage", return_value=storage), \
         patch.object(nt, "cfg", SimpleNamespace(workspace_dir=tmp_path)):
        out = nt.export_training_bundle("job-1")

    assert out["status"] == "exported"
    assert out["key"] == "training-corpus/job-1.json"
    storage.upload.assert_called_once()
    assert json.loads(str(uploaded["body"]))["job_id"] == "job-1"


def test_export_training_bundle_builds_from_db(tmp_path):
    clip = SimpleNamespace(
        rank=0,
        start_secs=0.0,
        end_secs=10.0,
        emotion="hype",
        transcript_text="hello",
        ensemble_score=0.8,
        llm_score=0.7,
        audio_score=0.6,
        spectral_score=0.5,
        flow_score=0.4,
        chat_score=0.3,
        llm_reason="funny",
    )
    job = SimpleNamespace(
        id="job-1",
        owner_id="u1",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source_duration_secs=120.0,
        config_snapshot={"target_clips": 5, "source_url": "https://secret"},
        clips=[clip],
    )
    user = SimpleNamespace(data_contribution_opt_in=True)
    storage = MagicMock()

    @asynccontextmanager
    async def fake_db_session():
        db = AsyncMock()

        async def get(model, pk):
            if pk == "job-1":
                return job
            if pk == "u1":
                return user
            return None

        db.get = AsyncMock(side_effect=get)
        db.refresh = AsyncMock()
        yield db

    with patch.object(nt, "db_session", fake_db_session), \
         patch.object(nt, "make_storage", return_value=storage), \
         patch.object(nt, "cfg", SimpleNamespace(workspace_dir=tmp_path)):
        out = nt.export_training_bundle("job-1")

    assert out["status"] == "exported"
    storage.upload.assert_called_once()


def test_export_training_bundle_skipped_when_job_missing():
    @asynccontextmanager
    async def fake_db_session():
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)
        yield db

    with patch.object(nt, "db_session", fake_db_session):
        out = nt.export_training_bundle("missing-job")

    assert out["status"] == "skipped"


def test_export_training_bundle_skipped_when_no_owner():
    job = SimpleNamespace(id="job-1", owner_id=None)

    @asynccontextmanager
    async def fake_db_session():
        db = AsyncMock()
        db.get = AsyncMock(return_value=job)
        yield db

    with patch.object(nt, "db_session", fake_db_session):
        out = nt.export_training_bundle("job-1")

    assert out["status"] == "skipped"


def test_smtp_settings_from_env(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setenv("SMTP_PORT", "2525")
    monkeypatch.setenv("SMTP_STARTTLS", "false")
    settings = smtp_settings_from_env()
    assert settings.host == "smtp.test"
    assert settings.port == 2525
    assert settings.starttls is False


def test_bug_report_recipient_from_env(monkeypatch):
    monkeypatch.setenv("BUG_REPORT_TO", "bugs@example.com")
    assert bug_report_recipient() == "bugs@example.com"


def test_bug_report_email_status_queued(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setenv("BUG_REPORT_TO", "bugs@example.com")
    from core.notify.email import bug_report_email_status

    assert bug_report_email_status() == "queued"


def test_bug_report_email_status_skipped_no_recipient(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.delenv("BUG_REPORT_TO", raising=False)
    from core.notify.email import bug_report_email_status

    assert bug_report_email_status() == "skipped_no_recipient"


def test_post_ops_webhook_success(monkeypatch):
    monkeypatch.setenv("N8N_OPS_WEBHOOK_URL", "https://n8n.test/webhook/ops")
    from core.notify import n8n_ops

    class FakeResp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    with patch("urllib.request.urlopen", return_value=FakeResp()):
        ok = n8n_ops.post_ops_webhook({"event": "beta_feedback", "message": "hi"})
    assert ok is True


def test_send_ops_webhook_task_posts_payload():
    report = SimpleNamespace(
        id="r1",
        severity="low",
        categories=["ui"],
        message="help",
        user_id=None,
        device_id="dev",
        job_id=None,
        environment={"kind": "beta_feedback"},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    with patch.object(nt, "_safe_async", return_value=report), patch.object(
        nt, "post_ops_webhook",
        return_value=True,
    ) as post:
        out = nt.send_ops_webhook("r1", "beta_feedback")
    assert out["status"] == "sent"
    post.assert_called_once()
    assert post.call_args[0][0]["event"] == "beta_feedback"


def test_send_email_skips_empty_recipient():
    settings = SMTPSettings(
        host="smtp.example.com", port=587, user="", password="",
        sender="noreply@test", starttls=True,
    )
    assert send_email(to="", subject="s", body="b", settings=settings) is False


def test_send_email_retries_then_fails():
    settings = SMTPSettings(
        host="smtp.example.com", port=587, user="u", password="p",
        sender="noreply@test", starttls=False,
    )
    with patch("core.notify.email.smtplib.SMTP", side_effect=OSError("down")), \
         patch("core.notify.email.time.sleep"):
        assert send_email(to="a@b.c", subject="s", body="b", settings=settings, max_retries=2) is False

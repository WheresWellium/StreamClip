"""Phase 3 — license-user linkage, bug reports, data contribution opt-in."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from backend.api.schemas import BugReportRequest
from backend.db.models import BugReport, InstallLicense, User, UserTier
from backend.db.session import get_sessionmaker
from core.notify.email import SMTPSettings, send_email
from core.tasks.notify_tasks import _anonymize_snapshot


def _unique_email() -> str:
    return f"phase3-{uuid.uuid4().hex[:10]}@example.com"


# ─── 3a. License-user linkage ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_links_license_by_email_and_syncs_tier(client):
    email = _unique_email()

    # Simulate a commerce-issued license bought with this email
    SessionMaker = get_sessionmaker()
    async with SessionMaker() as session:
        lic = InstallLicense(
            license_key_hash=uuid.uuid4().hex[:64],
            tier=UserTier.PRO,
            customer_email=email,
            status="issued",
        )
        session.add(lic)
        await session.commit()
        lic_id = lic.id

    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "hunter2secure"},
    )
    assert resp.status_code == 201
    user_id = resp.json()["user"]["id"]

    async with SessionMaker() as session:
        linked = await session.get(InstallLicense, lic_id)
        assert linked.user_id == user_id
        user = await session.get(User, user_id)
        assert user.tier == UserTier.PRO  # free → pro sync on link


@pytest.mark.asyncio
async def test_register_without_matching_license_stays_free(client):
    email = _unique_email()
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "hunter2secure"},
    )
    assert resp.status_code == 201
    assert resp.json()["user"]["tier"] == "free"


# ─── 3b. Bug reports ──────────────────────────────────────────────────────────

def test_bug_report_request_validation():
    ok = BugReportRequest(
        message="Captions are offset by two seconds on every clip.",
        categories=["captions", "captions", "performance"],
        severity="high",
    )
    assert ok.categories == ["captions", "performance"]  # deduped

    with pytest.raises(ValidationError):
        BugReportRequest(message="too short", categories=["ui"])
    with pytest.raises(ValidationError):
        BugReportRequest(
            message="Valid message but bogus category attached here.",
            categories=["nonsense"],
        )
    with pytest.raises(ValidationError):
        BugReportRequest(
            message="Valid message but no categories were selected.",
            categories=[],
        )


@pytest.mark.asyncio
async def test_submit_bug_report_creates_row_and_enqueues_email(client):
    with patch("backend.api.support.ops_webhook_status", return_value="skipped_unconfigured"), patch(
        "backend.api.support.bug_report_email_status",
        return_value="queued",
    ), patch("backend.api.support.dispatch_task") as dispatch:
        resp = await client.post(
            "/api/support/bug-reports",
            json={
                "message": "The vault page shows an empty grid after saving a clip.",
                "categories": ["vault", "ui"],
                "severity": "medium",
                "environment": {"page": "/vault", "user_agent": "pytest"},
            },
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "open"
    assert body["categories"] == ["vault", "ui"]
    assert body["email_notification"] == "queued"
    assert body["ops_notification"] == "skipped_unconfigured"
    dispatch.assert_called_once()
    assert dispatch.call_args.kwargs.get("queue") == "default"


@pytest.mark.asyncio
async def test_submit_bug_report_skips_email_when_smtp_unconfigured(client):
    with patch(
        "backend.api.support.bug_report_email_status",
        return_value="skipped_unconfigured",
    ), patch(
        "backend.api.support.ops_webhook_status",
        return_value="skipped_unconfigured",
    ), patch("backend.api.support.dispatch_task") as dispatch:
        resp = await client.post(
            "/api/support/bug-reports",
            json={
                "message": "The ingest step fails on every Twitch VOD I try.",
                "categories": ["ingest"],
                "severity": "high",
            },
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email_notification"] == "skipped_unconfigured"
    assert body["ops_notification"] == "skipped_unconfigured"
    dispatch.assert_not_called()


@pytest.mark.asyncio
async def test_submit_bug_report_enqueues_ops_webhook(client):
    with patch("backend.api.support.ops_webhook_status", return_value="queued"), patch(
        "backend.api.support.bug_report_email_status",
        return_value="skipped_unconfigured",
    ), patch("backend.api.support.dispatch_task") as dispatch:
        resp = await client.post(
            "/api/support/bug-reports",
            json={
                "message": "Export button does nothing after approve.",
                "categories": ["ui"],
                "severity": "medium",
            },
        )
    assert resp.status_code == 201
    assert resp.json()["ops_notification"] == "queued"
    dispatch.assert_called_once()


@pytest.mark.asyncio
async def test_submit_beta_feedback_creates_row_and_enqueues_ops(client):
    with patch("backend.api.support.ops_webhook_status", return_value="queued"), patch(
        "backend.api.support.dispatch_task",
    ) as dispatch:
        resp = await client.post(
            "/api/support/beta-feedback",
            json={
                "message": "How do I connect YouTube Shorts during beta?",
                "topic": "question",
                "environment": {"page": "/settings"},
            },
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["topic"] == "question"
    assert body["ops_notification"] == "queued"
    dispatch.assert_called_once()
    task_args = dispatch.call_args.kwargs["args"]
    assert task_args[1] == "beta_feedback"


@pytest.mark.asyncio
async def test_submit_bug_report_drops_unknown_job_id(client):
    with patch("backend.api.support.send_bug_report_email") as task:
        task.apply_async.return_value = MagicMock(id="notify-2")
        resp = await client.post(
            "/api/support/bug-reports",
            json={
                "message": "Job page crashed while the pipeline was running.",
                "categories": ["ui"],
                "job_id": "does-not-exist",
            },
        )
    assert resp.status_code == 201

    SessionMaker = get_sessionmaker()
    async with SessionMaker() as session:
        report = await session.get(BugReport, resp.json()["id"])
        assert report is not None
        assert report.job_id is None  # stale id dropped, not stored


@pytest.mark.asyncio
async def test_submit_bug_report_response_includes_notification_fields(client):
    with patch("backend.api.support.ops_webhook_status", return_value="skipped_unconfigured"), patch(
        "backend.api.support.bug_report_email_status",
        return_value="skipped_unconfigured",
    ):
        resp = await client.post(
            "/api/support/bug-reports",
            json={
                "message": "Captions render behind the subject on every clip.",
                "categories": ["captions"],
                "severity": "low",
            },
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email_notification"] == "skipped_unconfigured"
    assert body["ops_notification"] == "skipped_unconfigured"
    assert "id" in body


@pytest.mark.asyncio
async def test_submit_beta_feedback_response_shape(client):
    with patch("backend.api.support.ops_webhook_status", return_value="skipped_unconfigured"):
        resp = await client.post(
            "/api/support/beta-feedback",
            json={
                "message": "Can beta keys unlock distribution without signup?",
                "topic": "question",
            },
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["topic"] == "question"
    assert body["ops_notification"] == "skipped_unconfigured"
    assert body["status"]


# ─── Email notifier ───────────────────────────────────────────────────────────

def test_send_email_noop_when_unconfigured():
    settings = SMTPSettings(
        host="", port=587, user="", password="", sender="x@y.z", starttls=True,
    )
    assert send_email(to="a@b.c", subject="s", body="b", settings=settings) is False


def test_send_email_delivers_via_smtp():
    settings = SMTPSettings(
        host="smtp.example.com", port=587, user="u", password="p",
        sender="noreply@example.com", starttls=True,
    )
    with patch("core.notify.email.smtplib.SMTP") as smtp_cls:
        smtp = smtp_cls.return_value.__enter__.return_value
        ok = send_email(
            to="bugs@example.com", subject="test", body="hello",
            settings=settings,
        )
    assert ok is True
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("u", "p")
    smtp.send_message.assert_called_once()


# ─── 3c. Data contribution opt-in ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_privacy_settings_roundtrip(client):
    email = _unique_email()
    reg = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "hunter2secure"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    initial = await client.get("/api/settings/privacy", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["data_contribution_opt_in"] is False

    updated = await client.put(
        "/api/settings/privacy",
        json={"data_contribution_opt_in": True},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["data_contribution_opt_in"] is True

    confirmed = await client.get("/api/settings/privacy", headers=headers)
    assert confirmed.json()["data_contribution_opt_in"] is True


@pytest.mark.asyncio
async def test_privacy_settings_requires_auth(client):
    resp = await client.get("/api/settings/privacy")
    assert resp.status_code == 401


def test_feedback_environment_merges_extra():
    from backend.api.schemas import BetaFeedbackRequest
    from backend.api.support import _feedback_environment

    body = BetaFeedbackRequest(
        message="Need help connecting YouTube during beta testing.",
        topic="help",
        environment={"page": "/settings"},
    )
    env = _feedback_environment(body, {"wave": "phase0"})
    assert env["wave"] == "phase0"
    assert env["page"] == "/settings"
    assert env["kind"] == "beta_feedback"


def test_queue_support_notifications_bug_report_email():
    from backend.api import support

    with patch.object(support, "bug_report_email_status", return_value="queued"), patch.object(
        support, "ops_webhook_status", return_value="skipped_unconfigured",
    ), patch.object(support, "dispatch_task") as dispatch:
        email_status, ops_status = support._queue_support_notifications(
            "report-1", event="bug_report",
        )
    assert email_status == "queued"
    assert ops_status == "skipped_unconfigured"
    dispatch.assert_called_once()


def test_anonymize_snapshot_strips_pii():
    snap = {
        "target_clips": 5,
        "caption_style": "gaming_impact",
        "source_url": "https://twitch.tv/videos/123",
        "customer_email": "a@b.c",
    }
    cleaned = _anonymize_snapshot(snap)
    assert "source_url" not in cleaned
    assert "customer_email" not in cleaned
    assert cleaned["target_clips"] == 5
    assert _anonymize_snapshot({}) == {}

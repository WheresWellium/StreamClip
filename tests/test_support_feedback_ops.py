"""M4 — feedback ticket lifecycle, attachments, and admin ops."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.api import admin as admin_mod
from backend.api.schemas import BugReportAdminUpdateRequest
from backend.db.models import BugReport, FeedbackAttachment, User, UserTier
from backend.db.repositories import BugReportRepository, FeedbackAttachmentRepository
from backend.db.session import get_sessionmaker
from core.support.ticket_lifecycle import (
    InvalidBugReportTransition,
    resolve_next_status,
    validate_status_transition,
)


def _unique_email() -> str:
    return f"support-{uuid.uuid4().hex[:10]}@example.com"


async def _register_admin(client) -> tuple[str, str]:
    email = _unique_email()
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "hunter2secure"},
    )
    assert resp.status_code == 201
    user_id = resp.json()["user"]["id"]
    token = resp.json()["access_token"]

    SessionMaker = get_sessionmaker()
    async with SessionMaker() as session:
        user = await session.get(User, user_id)
        user.tier = UserTier.ADMIN
        await session.commit()

    return user_id, token


# ─── Lifecycle unit tests ────────────────────────────────────────────────────


def test_valid_status_transitions():
    validate_status_transition("open", "triage")
    validate_status_transition("resolved", "open")


def test_invalid_status_transition_raises():
    with pytest.raises(InvalidBugReportTransition):
        validate_status_transition("resolved", "assigned")


def test_resolve_next_status_auto_assign_from_open():
    assert resolve_next_status("open", requested_status=None, assigned_to="user-1") == "assigned"


def test_resolve_next_status_explicit_status():
    assert resolve_next_status("open", requested_status="triage", assigned_to=None) == "triage"


# ─── Repository tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bug_report_list_filtered_by_status(db):
    repo = BugReportRepository(db)
    open_report = await repo.create(
        categories=["ui"],
        severity="low",
        message="Open ticket for filter test",
    )
    await repo.create(
        categories=["ui"],
        severity="low",
        message="Resolved ticket for filter test",
        status="resolved",
    )
    await db.flush()

    rows = await repo.list_filtered(limit=10, status="open")
    ids = {r.id for r in rows}
    assert open_report.id in ids
    assert all(r.status == "open" for r in rows)


@pytest.mark.asyncio
async def test_feedback_attachment_link_to_report(db):
    repo = FeedbackAttachmentRepository(db)
    pending = await repo.create_pending(
        user_id=None,
        device_id="dev-support-1",
        storage_key="support/attachments/dev-support-1/a1/log.txt",
        filename="log.txt",
        content_type="text/plain",
        size_bytes=128,
    )
    report = await BugReportRepository(db).create(
        device_id="dev-support-1",
        categories=["ui"],
        severity="medium",
        message="Crash with attachment evidence attached here.",
    )
    await db.flush()

    linked = await repo.link_to_report(
        [pending.id],
        report_id=report.id,
        user_id=None,
        device_id="dev-support-1",
    )
    assert linked[0].bug_report_id == report.id


@pytest.mark.asyncio
async def test_feedback_attachment_rejects_wrong_owner(db):
    repo = FeedbackAttachmentRepository(db)
    pending = await repo.create_pending(
        user_id=None,
        device_id="dev-a",
        storage_key="support/attachments/dev-a/a1/log.txt",
        filename="log.txt",
        content_type="text/plain",
        size_bytes=128,
    )
    report = await BugReportRepository(db).create(
        device_id="dev-b",
        categories=["ui"],
        severity="medium",
        message="Wrong device should not link attachments here.",
    )
    await db.flush()

    with pytest.raises(ValueError, match="not owned"):
        await repo.link_to_report(
            [pending.id],
            report_id=report.id,
            user_id=None,
            device_id="dev-b",
        )


# ─── API integration ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_support_attachment_init_and_bug_report_link(client):
    with patch("backend.api.support.make_storage") as make_storage:
        storage = MagicMock()
        storage.presigned_put_url.return_value = "https://upload.example/put"
        make_storage.return_value = storage

        init_resp = await client.post(
            "/api/support/attachments/init",
            json={
                "filename": "screenshot.png",
                "content_type": "image/png",
                "size_bytes": 1024,
            },
        )
    assert init_resp.status_code == 201
    attachment_id = init_resp.json()["attachment_id"]

    with patch("backend.api.support.ops_webhook_status", return_value="skipped_unconfigured"), patch(
        "backend.api.support.bug_report_email_status",
        return_value="skipped_unconfigured",
    ):
        report_resp = await client.post(
            "/api/support/bug-reports",
            json={
                "message": "Export button fails after the latest deploy.",
                "categories": ["other"],
                "severity": "high",
                "attachment_ids": [attachment_id],
            },
        )
    assert report_resp.status_code == 201

    SessionMaker = get_sessionmaker()
    async with SessionMaker() as session:
        att = await session.get(FeedbackAttachment, attachment_id)
        assert att is not None
        assert att.bug_report_id == report_resp.json()["id"]


@pytest.mark.asyncio
async def test_admin_patch_bug_report_status_flow(client):
    admin_id, admin_token = await _register_admin(client)

    with patch("backend.api.support.ops_webhook_status", return_value="skipped_unconfigured"):
        create_resp = await client.post(
            "/api/support/bug-reports",
            json={
                "message": "Vault page spinner never stops loading clips.",
                "categories": ["vault"],
                "severity": "critical",
            },
        )
    report_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/admin/bug-reports/{report_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "triage"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "triage"

    assign_resp = await client.patch(
        f"/api/admin/bug-reports/{report_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"assigned_to": admin_id},
    )
    assert assign_resp.status_code == 200
    body = assign_resp.json()
    assert body["status"] == "assigned"
    assert body["assigned_to"] == admin_id

    resolve_resp = await client.patch(
        f"/api/admin/bug-reports/{report_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "resolved", "resolution_note": "Fixed in vault cache refresh."},
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_admin_patch_rejects_invalid_transition(client):
    _, admin_token = await _register_admin(client)

    with patch("backend.api.support.ops_webhook_status", return_value="skipped_unconfigured"):
        create_resp = await client.post(
            "/api/support/bug-reports",
            json={
                "message": "Cannot skip triage straight to resolved from open.",
                "categories": ["ui"],
                "severity": "low",
            },
        )
    report_id = create_resp.json()["id"]

    # open -> assigned is valid via assignee, but open -> resolved is valid too per TDD
    # resolved -> assigned is invalid
    await client.patch(
        f"/api/admin/bug-reports/{report_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "resolved"},
    )
    bad_resp = await client.patch(
        f"/api/admin/bug-reports/{report_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "assigned"},
    )
    assert bad_resp.status_code == 400


@pytest.mark.asyncio
async def test_admin_list_bug_reports_filters(client):
    _, admin_token = await _register_admin(client)

    with patch("backend.api.support.ops_webhook_status", return_value="skipped_unconfigured"):
        await client.post(
            "/api/support/bug-reports",
            json={
                "message": "Filter me by severity high for admin queue.",
                "categories": ["captions"],
                "severity": "high",
            },
        )
        await client.post(
            "/api/support/bug-reports",
            json={
                "message": "Filter me by severity low for admin queue.",
                "categories": ["ui"],
                "severity": "low",
            },
        )

    list_resp = await client.get(
        "/api/admin/bug-reports",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"severity": "high", "status": "open"},
    )
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert rows
    assert all(r["severity"] == "high" for r in rows)
    assert all(r["status"] == "open" for r in rows)


@pytest.mark.asyncio
async def test_admin_patch_bug_report_not_found():
    with patch.object(admin_mod, "BugReportRepository") as BR, patch.object(
        admin_mod, "require_admin", new_callable=AsyncMock, return_value="admin1",
    ):
        BR.return_value.get = AsyncMock(return_value=None)
        with pytest.raises(HTTPException) as exc:
            await admin_mod.update_bug_report(
                "missing",
                BugReportAdminUpdateRequest(status="triage"),
                admin_id="admin1",
                db=object(),
            )
        assert exc.value.status_code == 404

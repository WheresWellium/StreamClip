"""
StreamClip — Admin API

Operator-only endpoints. Requires an authenticated user with tier=admin.

POST /api/admin/licenses/{license_id}/revoke — revoke an issued license.
GET  /api/admin/bug-reports — list recent in-app bug reports.
PATCH /api/admin/bug-reports/{id} — update ticket status / assignment.
Revoked rows are retained so future activation attempts fail closed.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import BugReportAdminOut, BugReportAdminUpdateRequest
from backend.db.models import InstallLicense, UserTier
from backend.db.repositories import (
    BugReportRepository,
    InstallLicenseRepository,
    UserRepository,
)
from backend.db.session import get_db
from backend.middleware.auth import require_user_id
from backend.middleware.rate_limit import rate_limit_request
from core.errors import StreamClipError
from core.licensing import revoke_entitlement_hash
from core.support.metrics import refresh_support_ticket_metrics
from core.support.ticket_lifecycle import (
    UNSET,
    InvalidBugReportTransition,
    resolve_next_status,
)

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def require_admin(
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> str:
    """Reject any caller whose account tier is not admin."""
    user = await UserRepository(db).get(user_id)
    if user is None or user.tier != UserTier.ADMIN or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user_id


@router.get(
    "/bug-reports",
    response_model=list[BugReportAdminOut],
    dependencies=[Depends(rate_limit_request)],
)
async def list_bug_reports(
    admin_id: Annotated[str, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
    status: str | None = Query(None, description="open, triage, assigned, resolved"),
    severity: str | None = Query(None, description="low, medium, high, critical"),
    assigned_to: str | None = Query(None, description="Filter by assignee user id"),
    category: str | None = Query(None, description="Filter by category tag"),
    since: date | None = Query(None, description="Created on or after (ISO date)"),
) -> list[BugReportAdminOut]:
    del admin_id
    capped = min(max(limit, 1), 200)
    reports = await BugReportRepository(db).list_filtered(
        limit=capped,
        status=status,
        severity=severity,
        assigned_to=assigned_to,
        category=category,
        since=since,
    )
    await refresh_support_ticket_metrics(db)
    return [BugReportAdminOut.model_validate(r) for r in reports]


@router.patch(
    "/bug-reports/{report_id}",
    response_model=BugReportAdminOut,
    dependencies=[Depends(rate_limit_request)],
)
async def update_bug_report(
    report_id: str,
    body: BugReportAdminUpdateRequest,
    admin_id: Annotated[str, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BugReportAdminOut:
    repo = BugReportRepository(db)
    report = await repo.get(report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bug report not found")

    fields_set = body.model_fields_set
    assigned_update: str | None | object = UNSET
    if "assigned_to" in fields_set:
        assigned_update = body.assigned_to
    try:
        next_status = resolve_next_status(
            report.status,
            requested_status=body.status,
            assigned_to=assigned_update,
        )
    except InvalidBugReportTransition as exc:
        raise StreamClipError(
            str(exc),
            user_message="That status change is not allowed.",
            code="invalid_status_transition",
            http_status=400,
        ) from exc

    if body.assigned_to is not None:
        assignee = await UserRepository(db).get(body.assigned_to)
        if assignee is None or not assignee.is_active:
            raise StreamClipError(
                "Assignee not found",
                user_message="Assigned user was not found.",
                code="assignee_not_found",
                http_status=400,
            )

    updated = await repo.update_ticket(
        report,
        status=next_status,
        assigned_to=assigned_update,
        resolution_note=body.resolution_note,
    )
    await db.commit()
    await refresh_support_ticket_metrics(db)
    log.info(
        "bug_report_updated",
        report_id=report_id,
        admin_id=admin_id,
        status=updated.status,
        assigned_to=updated.assigned_to,
    )
    return BugReportAdminOut.model_validate(updated)


@router.post(
    "/licenses/{license_id}/revoke",
    dependencies=[Depends(rate_limit_request)],
)
async def revoke_license(
    license_id: str,
    admin_id: Annotated[str, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    repo = InstallLicenseRepository(db)
    lic = await repo.get(license_id)
    if lic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")

    already = lic.status == "revoked"
    if not already:
        await repo.revoke(lic)

        # Downgrade the linked user's tier to FREE if they have no other
        # activated license. Never deletes the user — only soft-adjusts tier.
        linked_user_id = lic.user_id
        if linked_user_id:
            other_active = await db.execute(
                select(InstallLicense.id).where(
                    InstallLicense.user_id == linked_user_id,
                    InstallLicense.status == "activated",
                    InstallLicense.id != lic.id,
                ).limit(1),
            )
            if other_active.scalar_one_or_none() is None:
                user = await UserRepository(db).get(linked_user_id)
                if user and user.tier != UserTier.FREE:
                    user.tier = UserTier.FREE
                    log.info(
                        "user_tier_downgraded_on_revoke",
                        user_id=linked_user_id,
                        license_id=license_id,
                    )

        await db.commit()
        revoke_entitlement_hash(lic.license_key_hash)
    log.info(
        "license_revoked",
        license_id=license_id,
        admin_id=admin_id,
        already_revoked=already,
        hash_prefix=lic.license_key_hash[:12],
    )
    return {
        "license_id": license_id,
        "status": "revoked",
        "note": (
            "Entitlement JWTs for this license_key_hash are blocklisted immediately "
            "via Redis / in-process set (streamclip:revoked_license_hashes)."
        ),
    }

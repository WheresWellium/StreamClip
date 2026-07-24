"""Refresh support ticket Prometheus gauges."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories import BugReportRepository
from core.pipeline_metrics import SUPPORT_TICKET_AGE_SECONDS, SUPPORT_TICKETS_OPEN

_OPEN_SEVERITIES = ("low", "medium", "high", "critical")


async def refresh_support_ticket_metrics(db: AsyncSession) -> None:
    repo = BugReportRepository(db)
    counts = await repo.count_open_by_severity()
    ages = await repo.open_ticket_ages_seconds()
    now = datetime.now(timezone.utc)

    for severity in _OPEN_SEVERITIES:
        SUPPORT_TICKETS_OPEN.labels(severity=severity).set(counts.get(severity, 0))

    for row in ages:
        created = row["created_at"]
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age_secs = max(0.0, (now - created).total_seconds())
        SUPPORT_TICKET_AGE_SECONDS.labels(severity=row["severity"]).observe(age_secs)

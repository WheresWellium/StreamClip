"""List recent bug reports and beta feedback from Postgres.

Usage (API container):

  docker compose exec api python scripts/list_support_reports.py
  docker compose exec api python scripts/list_support_reports.py --limit 20
  docker compose exec api python scripts/list_support_reports.py --kind feedback
  docker compose exec api python scripts/list_support_reports.py --kind bug
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from sqlalchemy import select

from backend.db.models import BugReport
from backend.db.session import get_sessionmaker


def _kind(report: BugReport) -> str:
    env = report.environment if isinstance(report.environment, dict) else {}
    if env.get("kind") == "beta_feedback":
        return "feedback"
    return "bug"


def _format_report(report: BugReport) -> dict[str, Any]:
    env = report.environment if isinstance(report.environment, dict) else {}
    row: dict[str, Any] = {
        "id": report.id,
        "kind": _kind(report),
        "status": report.status,
        "severity": report.severity,
        "categories": report.categories,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "user_id": report.user_id,
        "device_id": report.device_id,
        "job_id": report.job_id,
        "message_preview": (report.message or "")[:120],
    }
    if row["kind"] == "feedback":
        row["topic"] = env.get("topic")
    return row


async def _list(*, limit: int, kind_filter: str | None) -> int:
    SessionMaker = get_sessionmaker()
    async with SessionMaker() as db:
        result = await db.execute(
            select(BugReport).order_by(BugReport.created_at.desc()).limit(limit * 3),
        )
        reports = list(result.scalars().all())

    filtered: list[BugReport] = []
    for report in reports:
        kind = _kind(report)
        if kind_filter and kind != kind_filter:
            continue
        filtered.append(report)
        if len(filtered) >= limit:
            break

    if not filtered:
        print("No support reports found.", file=sys.stderr)
        return 0

    for row in (_format_report(r) for r in filtered):
        print(json.dumps(row, ensure_ascii=False))

    print(f"\n{len(filtered)} report(s).", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List bug reports and beta feedback.")
    parser.add_argument("--limit", type=int, default=50, help="Max rows (default: 50)")
    parser.add_argument(
        "--kind",
        choices=("bug", "feedback"),
        help="Filter by report kind",
    )
    args = parser.parse_args(argv)
    capped = max(1, min(args.limit, 200))
    return asyncio.run(_list(limit=capped, kind_filter=args.kind))


if __name__ == "__main__":
    raise SystemExit(main())

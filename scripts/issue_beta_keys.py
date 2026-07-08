"""Issue Phase 0 beta license keys (status=issued — testers activate in Settings).

Usage (from repo root, API container running):

  docker compose exec api python scripts/issue_beta_keys.py --emails a@example.com,b@example.com
  docker compose exec api python scripts/issue_beta_keys.py --csv cohort.csv
  docker compose exec api python scripts/issue_beta_keys.py --count 5 --email-domain example.com
  docker compose exec api python scripts/issue_beta_keys.py --emails you@example.com --tier admin

``--tier admin`` issues max-access keys (distribution + admin API + highest quotas).
Default ``--tier pro`` matches paid Pro entitlements.

CSV: one email per line (optional header ``email``).

Prints CSV to stdout: ``email,license_key,order_id,tier``. Keys are not emailed
automatically — paste into your invite template or n8n workflow later.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import secrets
import sys
from pathlib import Path

from backend.db.models import UserTier
from backend.db.repositories import InstallLicenseRepository
from backend.db.session import get_sessionmaker
from core.commerce.lemon_squeezy import generate_license_key
from core.licensing import hash_license_key


def _parse_emails_csv(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    start = 0
    if rows[0] and rows[0][0].strip().lower() == "email":
        start = 1
    emails: list[str] = []
    for row in rows[start:]:
        if not row:
            continue
        email = row[0].strip()
        if email and "@" in email:
            emails.append(email)
    return emails


def _placeholder_emails(count: int, domain: str) -> list[str]:
    slug = secrets.token_hex(3)
    return [f"beta-{slug}-{i + 1}@{domain}" for i in range(count)]


def _parse_tier(value: str) -> UserTier:
    normalized = value.strip().lower()
    if normalized == "pro":
        return UserTier.PRO
    if normalized == "admin":
        return UserTier.ADMIN
    raise ValueError(f"Unsupported tier {value!r}; use 'pro' or 'admin'.")


async def _issue(
    emails: list[str],
    *,
    dry_run: bool,
    order_prefix: str,
    tier: UserTier,
) -> int:
    if not emails:
        print("No emails to issue keys for.", file=sys.stderr)
        return 1

    deduped = list(dict.fromkeys(e.strip().lower() for e in emails if e.strip()))
    SessionMaker = get_sessionmaker()
    rows: list[tuple[str, str, str, str]] = []

    async with SessionMaker() as db:
        repo = InstallLicenseRepository(db)
        for idx, email in enumerate(deduped, start=1):
            license_key = generate_license_key()
            order_id = f"{order_prefix}-{idx:03d}"
            rows.append((email, license_key, order_id, tier.value))
            if dry_run:
                continue
            await repo.create_issued(
                license_key_hash=hash_license_key(license_key),
                tier=tier,
                order_id=order_id,
                customer_email=email,
            )
        if not dry_run:
            await db.commit()

    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(["email", "license_key", "order_id", "tier"])
    for row in rows:
        writer.writerow(row)

    mode = "dry-run" if dry_run else "issued"
    print(f"\n{len(rows)} {tier.value} key(s) {mode}.", file=sys.stderr)
    if not dry_run:
        print("Send keys manually or via n8n when ready.", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Issue beta license keys (pro or admin tier).")
    parser.add_argument(
        "--emails",
        help="Comma-separated tester emails",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="CSV file with one email per line",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="Issue N placeholder emails (requires --email-domain)",
    )
    parser.add_argument(
        "--email-domain",
        help="Domain for placeholder emails when using --count",
    )
    parser.add_argument(
        "--order-prefix",
        default="beta-phase0",
        help="Prefix for install_licenses.order_id (default: beta-phase0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print CSV without writing to the database",
    )
    parser.add_argument(
        "--tier",
        default="pro",
        choices=("pro", "admin"),
        help="License tier: pro (default) or admin (max access for power testers)",
    )
    args = parser.parse_args(argv)

    emails: list[str] = []
    if args.emails:
        emails.extend(e.strip() for e in args.emails.split(",") if e.strip())
    if args.csv:
        if not args.csv.is_file():
            print(f"CSV not found: {args.csv}", file=sys.stderr)
            return 1
        emails.extend(_parse_emails_csv(args.csv))
    if args.count:
        if not args.email_domain:
            print("--count requires --email-domain", file=sys.stderr)
            return 1
        emails.extend(_placeholder_emails(args.count, args.email_domain.strip()))

    if not emails:
        parser.error("Provide --emails, --csv, or --count with --email-domain")

    return asyncio.run(
        _issue(
            emails,
            dry_run=args.dry_run,
            order_prefix=args.order_prefix,
            tier=_parse_tier(args.tier),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())

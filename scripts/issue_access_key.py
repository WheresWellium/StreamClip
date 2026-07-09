"""Issue StreamClip license keys (email-bound or one-time) with JSONL activity log.

Examples (repo root, API container running):

  python scripts/issue_access_key.py
  python scripts/issue_access_key.py --email tester@example.com
  python scripts/issue_access_key.py --tier pro --email tester@example.com
  python scripts/issue_access_key.py --list --limit 20

Docker:

  docker compose exec api sh -c "PYTHONPATH=/app python scripts/issue_access_key.py"
  docker compose exec api sh -c "PYTHONPATH=/app python scripts/issue_access_key.py --email you@example.com"

Activity log (default): tmp/beta_key_activity.jsonl — gitignored, operator-only.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

from backend.db.models import UserTier
from backend.db.repositories import InstallLicenseRepository
from backend.db.session import get_sessionmaker
from core.commerce.lemon_squeezy import generate_license_key
from core.licensing import hash_license_key

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = REPO_ROOT / "tmp" / "beta_key_activity.jsonl"


def _parse_tier(value: str) -> UserTier:
    normalized = value.strip().lower()
    if normalized == "pro":
        return UserTier.PRO
    if normalized == "admin":
        return UserTier.ADMIN
    raise ValueError(f"Unsupported tier {value!r}; use 'pro' or 'admin'.")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _append_log(entry: dict[str, object], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, separators=(",", ":"), sort_keys=True) + "\n")


def _list_log(log_path: Path, limit: int) -> int:
    if not log_path.is_file():
        print("No activity log yet.", file=sys.stderr)
        return 0
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    for line in lines[-limit:]:
        print(line)
    print(f"\n{min(limit, len(lines))} of {len(lines)} log row(s).", file=sys.stderr)
    return 0


async def _issue(
    *,
    email: str | None,
    tier: UserTier,
    dry_run: bool,
    log_path: Path,
    order_prefix: str,
) -> int:
    license_key = generate_license_key()
    key_id = secrets.token_hex(4)
    order_id = f"{order_prefix}-{key_id}"
    kind = "email_bound" if email else "one_time"
    issued_at = _utc_now()

    row = {
        "ts": issued_at,
        "key_id": key_id,
        "kind": kind,
        "tier": tier.value,
        "email": email,
        "license_key": license_key,
        "order_id": order_id,
        "status": "dry_run" if dry_run else "issued",
    }

    if dry_run:
        _append_log(row, log_path)
        print(json.dumps(row, indent=2))
        print("\nDry run — no database write.", file=sys.stderr)
        return 0

    SessionMaker = get_sessionmaker()
    async with SessionMaker() as db:
        repo = InstallLicenseRepository(db)
        await repo.create_issued(
            license_key_hash=hash_license_key(license_key),
            tier=tier,
            order_id=order_id,
            customer_email=email,
        )
        await db.commit()

    _append_log(row, log_path)
    print(json.dumps(row, indent=2))
    print(
        f"\n{kind} {tier.value} key issued. Logged to {log_path}.",
        file=sys.stderr,
    )
    if kind == "one_time":
        print(
            "One-time key: no email binding — paste in Settings → License.",
            file=sys.stderr,
        )
    else:
        print(
            f"Email-bound: register/login as {email} before activating.",
            file=sys.stderr,
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Issue a license key (email-bound or one-time) with activity logging.",
    )
    parser.add_argument(
        "--email",
        help="Bind key to this email (omit for one-time key)",
    )
    parser.add_argument(
        "--tier",
        default="admin",
        choices=("pro", "admin"),
        help="License tier (default: admin = max access)",
    )
    parser.add_argument(
        "--order-prefix",
        default="beta",
        help="Prefix for install_licenses.order_id (default: beta)",
    )
    parser.add_argument(
        "--log-path",
        type=Path,
        default=DEFAULT_LOG,
        help=f"JSONL activity log path (default: {DEFAULT_LOG.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log + print key without writing to the database",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print recent activity log rows (JSONL)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Rows to show with --list (default: 20)",
    )
    args = parser.parse_args(argv)

    if args.list:
        return _list_log(args.log_path, max(1, args.limit))

    email = args.email.strip().lower() if args.email and args.email.strip() else None
    if email and "@" not in email:
        print("Invalid --email (missing @).", file=sys.stderr)
        return 1

    prefix = args.order_prefix.strip() or "beta"
    if not email:
        prefix = "otp"

    return asyncio.run(
        _issue(
            email=email,
            tier=_parse_tier(args.tier),
            dry_run=args.dry_run,
            log_path=args.log_path,
            order_prefix=prefix,
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())

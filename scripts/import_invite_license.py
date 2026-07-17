#!/usr/bin/env python3
"""Import an operator-issued invite license key into the local install DB.

Self-hosted testers run this once before activating in Settings → License when
the key was issued via ``issue_beta_keys.py`` (manual cohort) rather than LS.

Usage (repo root, API container running):

  docker compose exec -e PYTHONPATH=/app api python scripts/import_invite_license.py \\
      --key SCPRO-XXXX-XXXX-XXXX-XXXX --tier admin
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.db.models import UserTier
from backend.db.repositories import InstallLicenseRepository
from backend.db.session import get_sessionmaker
from core.licensing import hash_license_key

INVITE_KEY_RE = re.compile(r"^SCPRO-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}$")


def _parse_tier(value: str) -> UserTier:
    normalized = value.strip().lower()
    if normalized == "pro":
        return UserTier.PRO
    if normalized == "admin":
        return UserTier.ADMIN
    raise ValueError(f"Unsupported tier {value!r}; use 'pro' or 'admin'.")


def _normalize_key(raw: str) -> str:
    key = raw.strip().upper()
    if not INVITE_KEY_RE.match(key):
        raise ValueError(
            "License key must match SCPRO-XXXX-XXXX-XXXX-XXXX (hex groups).",
        )
    return key


async def _import_key(
    license_key: str,
    *,
    tier: UserTier,
    order_id: str | None,
    customer_email: str | None,
    dry_run: bool,
) -> int:
    key_hash = hash_license_key(license_key)
    SessionMaker = get_sessionmaker()
    async with SessionMaker() as db:
        repo = InstallLicenseRepository(db)
        existing = await repo.get_by_key_hash(key_hash)
        if existing is not None:
            print(
                f"Key already present (status={existing.status}, tier={existing.tier.value}).",
                file=sys.stderr,
            )
            return 0
        if dry_run:
            print(f"DRY-RUN would import {license_key[:12]}… as {tier.value}", file=sys.stderr)
            return 0
        await repo.create_issued(
            license_key_hash=key_hash,
            tier=tier,
            order_id=order_id,
            customer_email=customer_email,
        )
        await db.commit()
    print(f"Imported invite license ({tier.value}). Activate in Settings → License.", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import operator-issued invite key into local DB.")
    parser.add_argument("--key", required=True, help="SCPRO-… license key from invite email")
    parser.add_argument(
        "--tier",
        default="admin",
        choices=("pro", "admin"),
        help="Tier for this invite key (default: admin)",
    )
    parser.add_argument("--order-id", default=None, help="Optional order_id to store")
    parser.add_argument("--email", default=None, help="Optional customer email")
    parser.add_argument("--dry-run", action="store_true", help="Validate only; no DB write")
    args = parser.parse_args(argv)

    try:
        license_key = _normalize_key(args.key)
        tier = _parse_tier(args.tier)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return asyncio.run(
        _import_key(
            license_key,
            tier=tier,
            order_id=args.order_id,
            customer_email=args.email,
            dry_run=args.dry_run,
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())

"""Grant admin tier + activated Pro install license for local dev testing.

Usage (from repo root):
  docker compose exec api python scripts/grant_dev_pro.py

Optional env:
  DEV_GRANT_EMAIL=johncantwell@example.com  — upgrade only this user (default: all users)
"""

from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import select, update

from backend.db.models import InstallLicense, User, UserTier
from backend.db.repositories import InstallLicenseRepository
from backend.db.session import get_sessionmaker
from core.commerce.lemon_squeezy import generate_license_key
from core.licensing import activate_license_key, hash_license_key

MACHINE_ID = "streamclip-local-dev"


async def main() -> int:
    email_filter = os.environ.get("DEV_GRANT_EMAIL", "").strip().lower() or None
    SessionMaker = get_sessionmaker()

    async with SessionMaker() as db:
        if email_filter:
            result = await db.execute(select(User).where(User.email.ilike(email_filter)))
            users = list(result.scalars().all())
            if not users:
                print(f"No user found for DEV_GRANT_EMAIL={email_filter!r}", file=sys.stderr)
                return 1
        else:
            result = await db.execute(select(User))
            users = list(result.scalars().all())

        if users:
            user_ids = [u.id for u in users]
            await db.execute(
                update(User).where(User.id.in_(user_ids)).values(tier=UserTier.ADMIN),
            )
            print(f"Upgraded {len(users)} user(s) to admin:")
            for u in users:
                print(f"  - {u.email}")
        else:
            print("No users in database — skipping user tier upgrade.")

        repo = InstallLicenseRepository(db)
        existing = await repo.get_active()
        if existing and existing.tier in (UserTier.PRO, UserTier.ADMIN):
            print(f"Install license already active (tier={existing.tier.value}, machine={existing.machine_id}).")
            await db.commit()
            return 0

        license_key = generate_license_key()
        lic = await repo.create_issued(
            license_key_hash=hash_license_key(license_key),
            tier=UserTier.PRO,
            order_id="dev-grant",
            customer_email=email_filter or "dev@streamclip.local",
        )
        token, entitlement = activate_license_key(
            license_key,
            MACHINE_ID,
            tier=UserTier.PRO,
        )
        await repo.mark_activated(
            lic,
            machine_id=MACHINE_ID,
            entitlement_jwt=token,
            expires_at=entitlement.expires_at,
            count_activation=True,
        )
        await db.commit()

        print()
        print("Pro install license activated for local testing:")
        print(f"  License key: {license_key}")
        print(f"  Machine ID:  {MACHINE_ID}")
        print(f"  Tier:        {entitlement.tier.value}")
        print(f"  Expires:     {entitlement.expires_at}")
        print()
        print("Paste the license key in Settings → License if the UI still shows Free.")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

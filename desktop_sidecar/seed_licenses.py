"""Seed bundled cohort license hashes at desktop boot (W2 phase A)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import structlog

from backend.db.models import UserTier
from backend.db.repositories import InstallLicenseRepository
from backend.db.session import db_session, dispose_engine

log = structlog.get_logger(__name__)

_COHORT_REL = Path("packaging") / "cohort" / "cohort_licenses.json"


def cohort_seed_path(root: Path) -> Path:
    return root / _COHORT_REL


def _parse_tier(value: str) -> UserTier | None:
    normalized = value.strip().lower()
    if normalized == "pro":
        return UserTier.PRO
    if normalized == "admin":
        return UserTier.ADMIN
    log.warning("seed_license_unknown_tier", tier=value)
    return None


def _load_seed_file(path: Path) -> list[dict[str, str]] | None:
    if not path.is_file():
        log.info("seed_licenses_file_missing", path=str(path))
        return None
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("seed_licenses_read_failed", path=str(path), error=str(exc))
        return None
    if not isinstance(raw, dict):
        log.warning("seed_licenses_invalid_root", path=str(path))
        return None
    entries = raw.get("licenses")
    if not isinstance(entries, list):
        log.warning("seed_licenses_invalid_licenses", path=str(path))
        return None
    parsed: list[dict[str, str]] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        key_hash = item.get("key_hash")
        tier = item.get("tier")
        if isinstance(key_hash, str) and key_hash.strip() and isinstance(tier, str):
            parsed.append({"key_hash": key_hash.strip().lower(), "tier": tier.strip()})
    return parsed


async def _seed_async(entries: list[dict[str, str]]) -> int:
    inserted = 0
    async with db_session() as session:
        repo = InstallLicenseRepository(session)
        for entry in entries:
            tier = _parse_tier(entry["tier"])
            if tier is None:
                continue
            key_hash = entry["key_hash"]
            existing = await repo.get_by_key_hash(key_hash)
            if existing is not None:
                if existing.status == "revoked":
                    continue
                continue
            await repo.create_issued(license_key_hash=key_hash, tier=tier)
            inserted += 1
        await session.commit()
    return inserted


def seed_bundled_licenses(root: Path) -> int:
    """Insert bundled license hashes idempotently. Never blocks startup."""
    path = cohort_seed_path(root)
    entries = _load_seed_file(path)
    if not entries:
        return 0

    async def _run() -> int:
        try:
            return await _seed_async(entries)
        finally:
            await dispose_engine()

    try:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            inserted = asyncio.run(_run())
        else:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                inserted = executor.submit(asyncio.run, _run()).result()
    except Exception as exc:
        log.warning("seed_licenses_failed", error=str(exc))
        return 0

    if inserted:
        log.info("seed_licenses_inserted", count=inserted)
    return inserted

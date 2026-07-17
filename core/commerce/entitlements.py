"""Commerce entitlement helpers."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import UserTier
from backend.db.repositories import InstallLicenseRepository
from core.config import Settings, get_settings


def _audio_variant_ids(cfg: Settings) -> set[str]:
    raw = (cfg.commerce.audio_ingest_variant_ids or "").strip()
    if not raw:
        return set()
    return {part.strip() for part in raw.split(",") if part.strip()}


def variant_tier(variant_id: str | None, cfg: Settings | None = None) -> UserTier:
    """Map a Lemon Squeezy variant id to an install license tier."""
    cfg = cfg or get_settings()
    vid = (variant_id or "").strip()
    if vid and vid == (cfg.commerce.lemon_squeezy_beta_variant_id or "").strip():
        return UserTier.ADMIN
    if vid and vid == (cfg.commerce.lemon_squeezy_pro_variant_id or "").strip():
        return UserTier.PRO
    return UserTier.PRO


def variant_grants_audio_ingest(variant_id: str | None, cfg: Settings | None = None) -> bool:
    cfg = cfg or get_settings()
    if not variant_id:
        return False
    return variant_id.strip() in _audio_variant_ids(cfg)


def order_id_tags_audio_ingest(order_id: str | None) -> bool:
    return bool(order_id and str(order_id).startswith("audio:"))


def tag_audio_order_id(order_id: str | None) -> str | None:
    if not order_id:
        return None
    oid = str(order_id)
    if oid.startswith("audio:"):
        return oid
    return f"audio:{oid}"


async def scope_allows_audio_ingest(
    db: AsyncSession,
    *,
    machine_id: str | None,
    cfg: Settings | None = None,
) -> bool:
    cfg = cfg or get_settings()
    if cfg.features.audio_ingest:
        return True
    if not machine_id:
        return False
    lic = await InstallLicenseRepository(db).get_activated_by_machine_id(machine_id)
    return lic is not None and order_id_tags_audio_ingest(lic.order_id)

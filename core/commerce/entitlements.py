"""Commerce entitlement helpers — tiers plus capability claims."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import UserTier
from backend.db.repositories import InstallLicenseRepository
from core.config import Settings, get_settings

CAPABILITY_STUDIO = "studio"
CAPABILITY_PUBLISHER = "publisher"
CAPABILITY_AUDIO_INGEST = "audio_ingest"

CONSUMER_CAPABILITIES = (
    CAPABILITY_STUDIO,
    CAPABILITY_PUBLISHER,
    CAPABILITY_AUDIO_INGEST,
)


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


def normalize_capabilities(raw: Iterable[str] | None) -> list[str]:
    """Dedupe and keep only known consumer capabilities (stable order)."""
    if not raw:
        return []
    wanted = {str(c).strip() for c in raw if str(c).strip()}
    return [c for c in CONSUMER_CAPABILITIES if c in wanted]


def capabilities_for_tier(
    tier: UserTier,
    *,
    audio_ingest: bool = False,
) -> list[str]:
    """Derive capabilities when a license row has none stored yet.

    Legacy paid (PRO) keys receive studio + publisher. Beta/ADMIN install
    licenses receive every shipped consumer capability. FREE stays empty.
    ``admin`` as a *user* role remains operator-only elsewhere.
    """
    if tier == UserTier.FREE:
        return []
    if tier == UserTier.ADMIN:
        return list(CONSUMER_CAPABILITIES)
    caps = [CAPABILITY_STUDIO, CAPABILITY_PUBLISHER]
    if audio_ingest:
        caps.append(CAPABILITY_AUDIO_INGEST)
    return caps


def resolve_capabilities(
    *,
    tier: UserTier,
    stored: Sequence[str] | None = None,
    order_id: str | None = None,
    variant_id: str | None = None,
    cfg: Settings | None = None,
) -> list[str]:
    """Prefer explicit stored caps; otherwise derive from tier + audio signals."""
    normalized = normalize_capabilities(stored)
    if normalized:
        return normalized
    cfg = cfg or get_settings()
    audio = order_id_tags_audio_ingest(order_id) or variant_grants_audio_ingest(
        variant_id, cfg
    )
    return capabilities_for_tier(tier, audio_ingest=audio)


def has_capability(capabilities: Sequence[str] | None, capability: str) -> bool:
    return capability in normalize_capabilities(capabilities)


def tier_implies_publisher(tier: UserTier | str | None) -> bool:
    """Backward-compatible publisher gate from legacy FREE/PRO/ADMIN tiers."""
    if tier is None:
        return False
    value = tier.value if isinstance(tier, UserTier) else str(tier).lower()
    return value in {UserTier.PRO.value, UserTier.ADMIN.value}


def entitlements_dict(
    *,
    tier: UserTier,
    capabilities: Sequence[str],
) -> dict[str, Any]:
    caps = normalize_capabilities(capabilities)
    return {
        "tier": tier.value if isinstance(tier, UserTier) else str(tier),
        "capabilities": caps,
        "studio": CAPABILITY_STUDIO in caps,
        "publisher": CAPABILITY_PUBLISHER in caps,
        "audio_ingest": CAPABILITY_AUDIO_INGEST in caps,
    }


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
    if lic is None:
        return False
    caps = resolve_capabilities(
        tier=lic.tier,
        stored=getattr(lic, "capabilities", None),
        order_id=lic.order_id,
        cfg=cfg,
    )
    return has_capability(caps, CAPABILITY_AUDIO_INGEST)

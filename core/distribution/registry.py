"""Platform registry and metadata."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.distribution.credentials import OAuthAppCredentials
from core.distribution.tiktok import TikTokAdapter
from core.distribution.youtube import YouTubeShortsAdapter
from core.errors import StreamClipError


@dataclass(frozen=True)
class PlatformMeta:
    id: str
    label: str
    title_max: int
    max_duration_secs: float
    enabled: bool


PLATFORMS_V1: dict[str, PlatformMeta] = {
    "youtube_shorts": PlatformMeta(
        id="youtube_shorts",
        label="YouTube Shorts",
        title_max=100,
        max_duration_secs=60.0,
        enabled=True,
    ),
    "tiktok": PlatformMeta(
        id="tiktok",
        label="TikTok",
        title_max=150,
        max_duration_secs=60.0,
        enabled=False,
    ),
}


def list_platforms() -> list[PlatformMeta]:
    cfg = get_settings().distribution
    result: list[PlatformMeta] = []
    for meta in PLATFORMS_V1.values():
        if meta.id == "youtube_shorts" and not cfg.youtube_publish_enabled:
            continue
        if meta.id == "tiktok" and not cfg.tiktok_publish_enabled:
            continue
        result.append(
            PlatformMeta(
                id=meta.id,
                label=meta.label,
                title_max=meta.title_max,
                max_duration_secs=meta.max_duration_secs,
                enabled=True,
            ),
        )
    return result


def get_platform_meta(platform_id: str) -> PlatformMeta | None:
    return PLATFORMS_V1.get(platform_id)


def get_adapter(platform_id: str, app: OAuthAppCredentials) -> YouTubeShortsAdapter | TikTokAdapter:
    if platform_id == "youtube_shorts":
        return YouTubeShortsAdapter(app)
    if platform_id == "tiktok":
        return TikTokAdapter(app)
    raise StreamClipError(f"Unknown platform {platform_id}", code="unknown_platform")


async def build_adapter(db: AsyncSession, platform_id: str) -> YouTubeShortsAdapter | TikTokAdapter:
    from core.distribution.credentials import resolve_oauth_app

    app = await resolve_oauth_app(db, platform_id)
    return get_adapter(platform_id, app)

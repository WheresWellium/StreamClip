"""Resolve OAuth app credentials (BYO vs managed)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories import InstallOAuthAppRepository
from core.config import Settings, get_settings
from core.distribution.tokens import decrypt_secret
from core.errors import StreamClipError


@dataclass(frozen=True)
class OAuthAppCredentials:
    client_id: str
    client_secret: str
    redirect_uri: str


def default_redirect_uri(platform: str, cfg: Settings | None = None) -> str:
    cfg = cfg or get_settings()
    base = cfg.distribution.web_origin.rstrip("/")
    return f"{base}/api/distribution/oauth/{platform}/callback"


async def resolve_oauth_app(
    db: AsyncSession,
    platform: str,
    *,
    cfg: Settings | None = None,
) -> OAuthAppCredentials:
    cfg = cfg or get_settings()
    redirect = default_redirect_uri(platform, cfg)

    if cfg.distribution.mode == "managed":
        client_id, client_secret = _managed_env_credentials(platform, cfg)
        if not client_id or not client_secret:
            raise StreamClipError(
                "Managed OAuth not configured",
                user_message=f"Platform {platform} is not configured on this server.",
                code="oauth_not_configured",
            )
        return OAuthAppCredentials(client_id, client_secret, redirect)

    repo = InstallOAuthAppRepository(db)
    row = await repo.get(platform)
    if row and row.client_id and row.client_secret_enc:
        return OAuthAppCredentials(
            row.client_id,
            decrypt_secret(row.client_secret_enc),
            row.redirect_uri or redirect,
        )

    client_id, client_secret = _managed_env_credentials(platform, cfg)
    if client_id and client_secret:
        return OAuthAppCredentials(client_id, client_secret, redirect)

    raise StreamClipError(
        "OAuth app not configured",
        user_message="Add your OAuth app credentials in Settings → Platform apps (BYO).",
        code="oauth_not_configured",
    )


def _managed_env_credentials(platform: str, cfg: Settings) -> tuple[str, str]:
    if platform == "youtube_shorts":
        return (
            getattr(cfg.distribution, "youtube_client_id", "") or "",
            getattr(cfg.distribution, "youtube_client_secret", "") or "",
        )
    if platform == "tiktok":
        return (
            getattr(cfg.distribution, "tiktok_client_key", "") or "",
            getattr(cfg.distribution, "tiktok_client_secret", "") or "",
        )
    return "", ""

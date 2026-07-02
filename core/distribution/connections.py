"""Persist platform connections after OAuth."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.db.models import PlatformConnection
from backend.db.repositories import PlatformConnectionRepository
from core.distribution.base import PlatformCredentials
from core.distribution.registry import build_adapter
from core.distribution.tokens import decrypt_secret, encrypt_secret
from sqlalchemy.ext.asyncio import AsyncSession


async def save_platform_connection(
    db: AsyncSession,
    *,
    user_id: str,
    platform: str,
    account_label: str,
    credentials: PlatformCredentials,
) -> None:
    repo = PlatformConnectionRepository(db)
    await repo.upsert_tokens(
        user_id=user_id,
        platform=platform,
        account_label=account_label,
        access_token_enc=encrypt_secret(credentials.access_token),
        refresh_token_enc=encrypt_secret(credentials.refresh_token or "") if credentials.refresh_token else None,
        token_expires_at=credentials.expires_at,
        metadata_json={"scopes": []},
    )


def connection_to_credentials(connection: PlatformConnection) -> PlatformCredentials:
    return PlatformCredentials(
        platform_id=connection.platform,
        access_token=decrypt_secret(connection.access_token_enc or ""),
        refresh_token=decrypt_secret(connection.refresh_token_enc or "") if connection.refresh_token_enc else None,
        expires_at=connection.token_expires_at,
    )


async def ensure_fresh_credentials(
    db: AsyncSession,
    connection: PlatformConnection,
) -> PlatformCredentials:
    creds = connection_to_credentials(connection)
    if not creds.access_token:
        from core.distribution.errors import NoConnectionError

        raise NoConnectionError(connection.platform)

    expires = creds.expires_at
    if expires is not None and expires <= datetime.now(timezone.utc):
        if not creds.refresh_token:
            from core.errors import StreamClipError

            raise StreamClipError(
                "Token expired",
                user_message="Your platform connection expired. Reconnect in Distribution.",
                code="TOKEN_EXPIRED",
                http_status=401,
            )
        adapter = await build_adapter(db, connection.platform)
        refreshed = await adapter.refresh_token(creds.refresh_token)
        repo = PlatformConnectionRepository(db)
        await repo.upsert_tokens(
            user_id=connection.user_id,
            platform=connection.platform,
            account_label=connection.account_label,
            access_token_enc=encrypt_secret(refreshed.access_token),
            refresh_token_enc=encrypt_secret(refreshed.refresh_token or "") if refreshed.refresh_token else None,
            token_expires_at=refreshed.expires_at,
            metadata_json=connection.metadata_json,
        )
        await db.flush()
        return refreshed
    return creds

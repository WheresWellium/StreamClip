"""TikTok platform adapter (OAuth + Content Posting API)."""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone

import httpx

from core.distribution.base import (
    PlatformCredentials,
    PublishMetadata,
    PublishResult,
    ScheduleResult,
)
from core.distribution.credentials import OAuthAppCredentials
from core.errors import StreamClipError

TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_SCOPES = ["user.info.basic", "video.upload"]


class TikTokAdapter:
    platform_id = "tiktok"

    def __init__(self, app: OAuthAppCredentials) -> None:
        self._app = app

    async def get_auth_url(self, redirect_uri: str, *, state: str) -> str:
        params = {
            "client_key": self._app.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": ",".join(TIKTOK_SCOPES),
            "state": state,
        }
        return f"{TIKTOK_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> PlatformCredentials:
        data = await self._token_request(
            {
                "client_key": self._app.client_id,
                "client_secret": self._app.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        return self._credentials_from_token_response(data)

    async def refresh_token(self, refresh_token: str) -> PlatformCredentials:
        data = await self._token_request(
            {
                "client_key": self._app.client_id,
                "client_secret": self._app.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        creds = self._credentials_from_token_response(data)
        if not creds.refresh_token:
            return PlatformCredentials(
                platform_id=self.platform_id,
                access_token=creds.access_token,
                refresh_token=refresh_token,
                expires_at=creds.expires_at,
            )
        return creds

    async def fetch_user_label(self, access_token: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://open.tiktokapis.com/v2/user/info/",
                params={"fields": "display_name,open_id"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if not resp.is_success:
            return "TikTok"
        user = (resp.json().get("data") or {}).get("user") or {}
        return user.get("display_name") or user.get("open_id") or "TikTok"

    async def publish(
        self,
        clip_storage_key: str,
        metadata: PublishMetadata,
        credentials: PlatformCredentials,
    ) -> PublishResult:
        _ = clip_storage_key, metadata, credentials
        return PublishResult(status="pending", message="TikTok upload pending worker integration.")

    async def schedule(
        self,
        clip_storage_key: str,
        metadata: PublishMetadata,
        credentials: PlatformCredentials,
        publish_at: datetime,
    ) -> ScheduleResult:
        _ = clip_storage_key, metadata, credentials
        return ScheduleResult(status="scheduled", scheduled_at=publish_at)

    async def revoke(self, credentials: PlatformCredentials) -> None:
        _ = credentials

    async def _token_request(self, payload: dict[str, str]) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                TIKTOK_TOKEN_URL,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if not resp.is_success:
            raise StreamClipError(
                "TikTok OAuth failed",
                user_message="Could not connect TikTok. Check your developer app settings.",
                code="oauth_exchange_failed",
            )
        body = resp.json()
        if body.get("error"):
            raise StreamClipError(
                str(body.get("error")),
                user_message="TikTok authorization failed.",
                code="oauth_exchange_failed",
            )
        return body.get("data") or body

    def _credentials_from_token_response(self, data: dict) -> PlatformCredentials:
        expires_at = None
        if "expires_in" in data:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(data["expires_in"]))
        return PlatformCredentials(
            platform_id=self.platform_id,
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
        )

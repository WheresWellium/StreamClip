"""TikTok platform adapter (OAuth + Content Posting API).

Upload uses the *inbox* flow (``video.upload`` scope): the video lands in the
user's TikTok inbox and they finish posting inside the TikTok app. Direct
public posting requires the ``video.publish`` scope and a TikTok app audit,
so it's deliberately not used here.
"""

from __future__ import annotations

import asyncio
import math
import urllib.parse
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
TIKTOK_INBOX_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
TIKTOK_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
TIKTOK_SCOPES = ["user.info.basic", "video.upload"]

# TikTok chunking rules: single chunk up to 64 MB; larger files use chunks
# of 5–64 MB (all but the last must be the full chunk size).
_MAX_CHUNK_BYTES = 64 * 1024 * 1024
_STATUS_POLL_SECS = 3.0
_STATUS_POLL_MAX = 40  # ~2 minutes of server-side processing


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
        return PublishResult(
            status="pending",
            message="TikTok upload is performed by the publish worker.",
        )

    async def upload_video_file(
        self,
        video_path: Path,
        metadata: PublishMetadata,
        access_token: str,
        *,
        on_progress: Callable[[str, float], None] | None = None,
    ) -> PublishResult:
        """Upload a video to the user's TikTok inbox (Content Posting API).

        The user gets a TikTok notification and finishes the post (caption,
        privacy, publish) inside the app — that's the inbox-flow contract.
        """
        _ = metadata  # caption is chosen in the TikTok app for inbox uploads
        if not video_path.is_file():
            return PublishResult(status="failed", message="Video file not found for upload.")

        if on_progress:
            on_progress("upload", 0.1)

        file_size = video_path.stat().st_size
        chunk_size = min(file_size, _MAX_CHUNK_BYTES)
        total_chunks = max(1, math.ceil(file_size / chunk_size))
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=600.0) as client:
            init_resp = await client.post(
                TIKTOK_INBOX_INIT_URL,
                headers={**headers, "Content-Type": "application/json; charset=UTF-8"},
                json={
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": file_size,
                        "chunk_size": chunk_size,
                        "total_chunk_count": total_chunks,
                    },
                },
            )
            init_body = init_resp.json() if init_resp.content else {}
            error = (init_body.get("error") or {}).get("code", "ok")
            if not init_resp.is_success or error != "ok":
                detail = (init_body.get("error") or {}).get("message") or init_resp.text[:300]
                return PublishResult(
                    status="failed",
                    message=f"TikTok rejected upload session: {detail}",
                )

            data = init_body.get("data") or {}
            publish_id = data.get("publish_id")
            upload_url = data.get("upload_url")
            if not publish_id or not upload_url:
                return PublishResult(
                    status="failed",
                    message="TikTok did not return an upload URL.",
                )

            if on_progress:
                on_progress("upload", 0.3)

            with video_path.open("rb") as fh:
                for chunk_index in range(total_chunks):
                    start = chunk_index * chunk_size
                    chunk = fh.read(chunk_size)
                    end = start + len(chunk) - 1
                    upload_resp = await client.put(
                        upload_url,
                        headers={
                            "Content-Type": "video/mp4",
                            "Content-Length": str(len(chunk)),
                            "Content-Range": f"bytes {start}-{end}/{file_size}",
                        },
                        content=chunk,
                    )
                    if not upload_resp.is_success:
                        return PublishResult(
                            status="failed",
                            message=f"TikTok upload failed: {upload_resp.text[:300]}",
                        )
                    if on_progress:
                        on_progress("upload", 0.3 + 0.5 * (chunk_index + 1) / total_chunks)

            if on_progress:
                on_progress("finalize", 0.85)

            return await self._await_processing(client, headers, publish_id)

    async def _await_processing(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        publish_id: str,
    ) -> PublishResult:
        """Poll status/fetch until TikTok accepts the inbox upload."""
        for _ in range(_STATUS_POLL_MAX):
            resp = await client.post(
                TIKTOK_STATUS_URL,
                headers={**headers, "Content-Type": "application/json; charset=UTF-8"},
                json={"publish_id": publish_id},
            )
            body = resp.json() if resp.content else {}
            status = ((body.get("data") or {}).get("status") or "").upper()
            if status == "SEND_TO_USER_INBOX":
                return PublishResult(
                    status="published",
                    message=(
                        "Sent to the TikTok inbox — open the TikTok app "
                        "notification to finish posting."
                    ),
                )
            if status == "FAILED":
                reason = (body.get("data") or {}).get("fail_reason") or "unknown"
                return PublishResult(
                    status="failed",
                    message=f"TikTok processing failed: {reason}",
                )
            await asyncio.sleep(_STATUS_POLL_SECS)
        # Upload was accepted; processing just outlived our poll budget.
        return PublishResult(
            status="published",
            message="Uploaded to TikTok — check the TikTok app inbox to finish posting.",
        )

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

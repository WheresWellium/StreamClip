"""YouTube Shorts platform adapter (OAuth + upload)."""

from __future__ import annotations

import urllib.parse
from collections.abc import AsyncIterator, Callable
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

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
UPLOAD_CHUNK_BYTES = 8 * 1024 * 1024


async def _stream_file(path: Path, chunk_size: int = UPLOAD_CHUNK_BYTES) -> AsyncIterator[bytes]:
    """Yield the video in chunks so multi-hundred-MB clips never sit in RAM."""
    with path.open("rb") as fh:
        while chunk := fh.read(chunk_size):
            yield chunk


class YouTubeShortsAdapter:
    platform_id = "youtube_shorts"

    def __init__(self, app: OAuthAppCredentials) -> None:
        self._app = app

    async def get_auth_url(self, redirect_uri: str, *, state: str) -> str:
        params = {
            "client_id": self._app.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(YOUTUBE_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> PlatformCredentials:
        data = await self._token_request(
            {
                "code": code,
                "client_id": self._app.client_id,
                "client_secret": self._app.client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        return self._credentials_from_token_response(data)

    async def refresh_token(self, refresh_token: str) -> PlatformCredentials:
        data = await self._token_request(
            {
                "refresh_token": refresh_token,
                "client_id": self._app.client_id,
                "client_secret": self._app.client_secret,
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

    async def fetch_channel_label(self, access_token: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={"part": "snippet", "mine": "true"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if not resp.is_success:
            return "YouTube"
        items = resp.json().get("items") or []
        if not items:
            return "YouTube"
        return items[0].get("snippet", {}).get("title") or "YouTube"

    async def publish(
        self,
        clip_storage_key: str,
        metadata: PublishMetadata,
        credentials: PlatformCredentials,
    ) -> PublishResult:
        _ = clip_storage_key, metadata, credentials
        return PublishResult(
            status="pending",
            message="YouTube upload is performed by the publish worker.",
        )

    async def upload_video_file(
        self,
        video_path: Path,
        metadata: PublishMetadata,
        access_token: str,
        *,
        on_progress: Callable[[str, float], None] | None = None,
    ) -> PublishResult:
        if not video_path.is_file():
            return PublishResult(status="failed", message="Video file not found for upload.")

        if on_progress:
            on_progress("upload", 0.1)

        snippet = {
            "title": metadata.title[:100] or "StreamClip Short",
            "description": metadata.description[:5000],
            "categoryId": "22",
        }
        status_body = {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        }
        init_body = {"snippet": snippet, "status": status_body}
        file_size = video_path.stat().st_size

        async with httpx.AsyncClient(timeout=600.0) as client:
            init_resp = await client.post(
                YOUTUBE_UPLOAD_URL,
                params={"uploadType": "resumable", "part": "snippet,status"},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                    "X-Upload-Content-Type": "video/mp4",
                    "X-Upload-Content-Length": str(file_size),
                },
                json=init_body,
            )
            if not init_resp.is_success:
                detail = init_resp.text[:500]
                return PublishResult(
                    status="failed",
                    message=f"YouTube rejected upload session: {detail}",
                )

            upload_url = init_resp.headers.get("Location")
            if not upload_url:
                return PublishResult(status="failed", message="YouTube did not return an upload URL.")

            if on_progress:
                on_progress("upload", 0.35)

            upload_resp = await client.put(
                upload_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "video/mp4",
                    "Content-Length": str(file_size),
                },
                content=_stream_file(video_path),
            )

            if on_progress:
                on_progress("finalize", 0.9)

            if not upload_resp.is_success:
                detail = upload_resp.text[:500]
                return PublishResult(
                    status="failed",
                    message=f"YouTube upload failed: {detail}",
                )

            body = upload_resp.json()
            video_id = body.get("id")
            if not video_id:
                return PublishResult(status="failed", message="YouTube did not return a video id.")

            external_url = f"https://www.youtube.com/shorts/{video_id}"
            return PublishResult(
                status="published",
                external_url=external_url,
                message="Published to YouTube Shorts",
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
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": credentials.access_token},
            )

    async def _token_request(self, payload: dict[str, str]) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(GOOGLE_TOKEN_URL, data=payload)
        if not resp.is_success:
            raise StreamClipError(
                "OAuth token exchange failed",
                user_message="Could not connect YouTube. Check your OAuth app settings.",
                code="oauth_exchange_failed",
            )
        return resp.json()

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

"""Platform distribution adapter protocol."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class PlatformCredentials:
    platform_id: str
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None


@dataclass(frozen=True)
class PublishMetadata:
    title: str
    description: str
    tags: list[str]


@dataclass(frozen=True)
class PublishResult:
    status: str
    external_url: str | None = None
    message: str = ""


@dataclass(frozen=True)
class ScheduleResult:
    status: str
    scheduled_at: datetime
    message: str = ""


class PlatformAdapter(Protocol):
    platform_id: str

    async def get_auth_url(self, redirect_uri: str) -> str: ...

    async def exchange_code(self, code: str, redirect_uri: str) -> PlatformCredentials: ...

    async def publish(
        self,
        clip_storage_key: str,
        metadata: PublishMetadata,
        credentials: PlatformCredentials,
    ) -> PublishResult: ...

    async def schedule(
        self,
        clip_storage_key: str,
        metadata: PublishMetadata,
        credentials: PlatformCredentials,
        publish_at: datetime,
    ) -> ScheduleResult: ...

    async def revoke(self, credentials: PlatformCredentials) -> None: ...

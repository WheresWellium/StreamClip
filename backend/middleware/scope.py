"""Request scope: resolves user + device identity for job ownership."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from backend.middleware.auth import get_current_user_id, get_device_id
from core.config import get_settings
from core.errors import DeviceIdRequiredError


@dataclass(frozen=True)
class RequestScope:
    user_id: str | None
    device_id: str | None


async def get_request_scope(
    user_id: Annotated[str | None, Depends(get_current_user_id)],
    device_id: Annotated[str | None, Depends(get_device_id)],
) -> RequestScope:
    cfg = get_settings()
    if user_id is None and cfg.auth.device_scoped_anonymous and not device_id:
        # Domain error keeps the {"code": ...} error contract the API promises
        raise DeviceIdRequiredError("Missing X-Device-Id for anonymous request")
    return RequestScope(user_id=user_id, device_id=device_id)

"""Device onboarding API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import OnboardingCompleteRequest, OnboardingCompleteResponse
from backend.db.repositories import DeviceRepository
from backend.db.session import get_db
from backend.middleware.auth import get_device_id
from backend.middleware.rate_limit import rate_limit_request

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.post(
    "/onboarding-complete",
    response_model=OnboardingCompleteResponse,
    dependencies=[Depends(rate_limit_request)],
)
async def complete_onboarding(
    body: OnboardingCompleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    header_device: Annotated[str | None, Depends(get_device_id)] = None,
) -> OnboardingCompleteResponse:
    device_id = body.device_id or header_device
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id required")
    repo = DeviceRepository(db)
    await repo.mark_onboarding_complete(device_id)
    await db.commit()
    return OnboardingCompleteResponse(device_id=device_id)

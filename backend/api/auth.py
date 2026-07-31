"""
StreamClip — Authentication API

POST /api/auth/register  — create account
POST /api/auth/login     — issue access + refresh tokens
POST /api/auth/refresh   — rotate access token
GET  /api/auth/me        — current user profile
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    AuthResponse,
    ChangePasswordRequest,
    ClaimDeviceRequest,
    ClaimDeviceResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    UserOut,
)
from backend.db.session import get_db
from backend.middleware.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user_id,
    get_device_id,
    require_user_id,
)
from backend.services.auth_service import AuthService
from backend.services.license_link import link_licenses_by_email
from backend.middleware.rate_limit import rate_limit_auth, rate_limit_request
from backend.db.repositories import DeviceRepository
from core.config import get_settings
from core.errors import AuthError
from core.task_dispatch import dispatch_task
from core.tasks.notify_tasks import send_password_reset_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

_FORGOT_PASSWORD_MESSAGE = (
    "If an account exists for that email, a reset link has been sent."
)


def _get_service(db: AsyncSession) -> AuthService:
    return AuthService(db, get_settings())


def _auth_response(user, *, remember_me: bool = True) -> AuthResponse:
    cfg = get_settings()
    return AuthResponse(
        access_token=create_access_token(user.id, cfg),
        refresh_token=create_refresh_token(user.id, cfg, remember_me=remember_me),
        user=UserOut.model_validate(user),
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_auth)],
)
async def register(
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    svc = _get_service(db)
    user = await svc.register(body.email, body.password, display_name=body.display_name)
    # Phase 3a — claim any licenses purchased with this email
    await link_licenses_by_email(db, user)
    await db.commit()
    return _auth_response(user, remember_me=True)


@router.post(
    "/login",
    response_model=AuthResponse,
    dependencies=[Depends(rate_limit_auth)],
)
async def login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    svc = _get_service(db)
    user = await svc.authenticate(body.email, body.password)
    return _auth_response(user, remember_me=body.remember_me)


@router.post(
    "/refresh",
    response_model=AuthResponse,
    dependencies=[Depends(rate_limit_request)],
)
async def refresh(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    cfg = get_settings()
    try:
        payload = decode_token(body.refresh_token, cfg)
    except AuthError as exc:
        raise AuthError(exc.user_message) from exc
    if payload.get("type") != "refresh":
        raise AuthError("Invalid refresh token")
    user_id = payload["sub"]
    remember_me = bool(payload.get("rem", True))
    svc = _get_service(db)
    user = await svc.get_active_user(user_id)
    return _auth_response(user, remember_me=remember_me)


@router.get(
    "/me",
    response_model=UserOut,
    dependencies=[Depends(rate_limit_request)],
)
async def me(
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserOut:
    svc = _get_service(db)
    user = await svc.get_active_user(user_id)
    return UserOut.model_validate(user)


@router.patch(
    "/me",
    response_model=UserOut,
    dependencies=[Depends(rate_limit_request)],
)
async def update_me(
    body: UpdateProfileRequest,
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserOut:
    svc = _get_service(db)
    user = await svc.update_profile(user_id, display_name=body.display_name)
    await db.commit()
    return UserOut.model_validate(user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit_request)],
)
async def change_password(
    body: ChangePasswordRequest,
    user_id: Annotated[str, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    svc = _get_service(db)
    await svc.change_password(user_id, body.current_password, body.new_password)
    await db.commit()
    return MessageResponse(message="Password updated")


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit_auth)],
)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    svc = _get_service(db)
    result = await svc.create_password_reset(body.email)
    if result is not None:
        raw_token, user = result
        await db.commit()
        cfg = get_settings()
        reset_url = (
            f"{cfg.distribution.web_origin.rstrip('/')}/reset-password?token={raw_token}"
        )
        dispatch_task(send_password_reset_email, args=(user.email, reset_url), queue="default")
    return MessageResponse(message=_FORGOT_PASSWORD_MESSAGE)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit_auth)],
)
async def reset_password(
    body: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    svc = _get_service(db)
    await svc.reset_password(body.token, body.new_password)
    await db.commit()
    return MessageResponse(message="Password reset. You can sign in with your new password.")


@router.post(
    "/claim-device",
    response_model=ClaimDeviceResponse,
    dependencies=[Depends(rate_limit_request)],
)
async def claim_device(
    body: ClaimDeviceRequest,
    user_id: Annotated[str, Depends(require_user_id)],
    header_device: Annotated[str | None, Depends(get_device_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClaimDeviceResponse:
    device_id = body.device_id or header_device
    if not device_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="device_id required")
    repo = DeviceRepository(db)
    count = await repo.claim_for_user(device_id, user_id)
    await db.commit()
    return ClaimDeviceResponse(jobs_claimed=count, device_id=device_id)

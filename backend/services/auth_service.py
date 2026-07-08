"""
StreamClip — Authentication service
"""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import User
from backend.db.repositories import PasswordResetRepository, UserRepository
from backend.middleware.auth import hash_password, verify_password
from core.config import Settings
from core.errors import AuthError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(self, db: AsyncSession, cfg: Settings) -> None:
        self.db = db
        self.cfg = cfg
        self.users = UserRepository(db)
        self.reset_tokens = PasswordResetRepository(db)

    def _validate_password(self, password: str) -> None:
        if len(password) < 8:
            raise AuthError("Password must be at least 8 characters")

    async def register(
        self,
        email: str,
        password: str,
        *,
        display_name: str | None = None,
    ) -> User:
        normalised = email.strip().lower()
        if not _EMAIL_RE.match(normalised):
            raise AuthError("Invalid email address")
        self._validate_password(password)
        existing = await self.users.get_by_email(normalised)
        if existing is not None:
            raise AuthError("Email already registered", user_message="Email already registered")
        return await self.users.create(
            email=normalised,
            hashed_password=hash_password(password),
            display_name=display_name or normalised.split("@")[0],
        )

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email.strip().lower())
        if user is None or not user.hashed_password:
            raise AuthError("Invalid email or password")
        if not verify_password(password, user.hashed_password):
            raise AuthError("Invalid email or password")
        if not user.is_active:
            raise AuthError("Account is disabled")
        return user

    async def get_active_user(self, user_id: str) -> User:
        user = await self.users.get(user_id)
        if user is None or not user.is_active:
            raise AuthError("User not found")
        return user

    async def update_profile(self, user_id: str, *, display_name: str) -> User:
        name = display_name.strip()
        if not name:
            raise AuthError("Display name is required")
        if len(name) > 120:
            raise AuthError("Display name is too long")
        user = await self.get_active_user(user_id)
        await self.users.update_display_name(user.id, name)
        user.display_name = name
        return user

    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> None:
        user = await self.get_active_user(user_id)
        if not user.hashed_password or not verify_password(current_password, user.hashed_password):
            raise AuthError("Current password is incorrect")
        self._validate_password(new_password)
        if verify_password(new_password, user.hashed_password):
            raise AuthError("New password must be different from the current password")
        await self.users.update_password(user.id, hash_password(new_password))

    async def create_password_reset(self, email: str) -> tuple[str, User] | None:
        """Return (raw_token, user) when a reset should be emailed; None if user unknown."""
        user = await self.users.get_by_email(email.strip().lower())
        if user is None or not user.is_active or not user.hashed_password:
            return None
        raw_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self.cfg.auth.password_reset_expire_minutes,
        )
        await self.reset_tokens.invalidate_for_user(user.id)
        await self.reset_tokens.create(
            user_id=user.id,
            token_hash=_hash_reset_token(raw_token),
            expires_at=expires_at,
        )
        return raw_token, user

    async def reset_password(self, raw_token: str, new_password: str) -> User:
        token_hash = _hash_reset_token(raw_token.strip())
        row = await self.reset_tokens.get_valid_by_hash(token_hash)
        if row is None:
            raise AuthError("Invalid or expired reset link")
        self._validate_password(new_password)
        user = await self.get_active_user(row.user_id)
        await self.users.update_password(user.id, hash_password(new_password))
        await self.reset_tokens.mark_used(row.id)
        return user

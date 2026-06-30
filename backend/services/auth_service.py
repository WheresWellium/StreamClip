"""
StreamClip — Authentication service
"""

from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import User
from backend.db.repositories import UserRepository
from backend.middleware.auth import hash_password, verify_password
from core.config import Settings
from core.errors import AuthError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthService:
    def __init__(self, db: AsyncSession, cfg: Settings) -> None:
        self.db = db
        self.cfg = cfg
        self.users = UserRepository(db)

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
        if len(password) < 8:
            raise AuthError("Password must be at least 8 characters")
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

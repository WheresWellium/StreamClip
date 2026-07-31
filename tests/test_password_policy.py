"""Password policy unit tests — single source of truth for auth strength."""

from __future__ import annotations

import pytest

from core.password_policy import (
    BCRYPT_MAX_BYTES,
    MIN_PASSWORD_LENGTH,
    PasswordPolicyError,
    validate_password,
)


@pytest.mark.parametrize(
    "password",
    [
        "password12345",
        "hunter2secure",
        "Abcdefg1",
        "good-pass!",
    ],
)
def test_accepts_reasonable_passwords(password: str) -> None:
    validate_password(password)  # does not raise


@pytest.mark.parametrize(
    "password,needle",
    [
        ("", "required"),
        ("short1", "at least"),
        ("abcdefgh", "letters and at least one number"),
        ("12345678", "letters and at least one number"),
        ("password1", "too common"),
        ("qwerty123", "too common"),
        ("x" * (BCRYPT_MAX_BYTES + 1), "too long to hash"),
        ("Ab1" + ("x" * 130), "at most"),
    ],
)
def test_rejects_weak_passwords(password: str, needle: str) -> None:
    with pytest.raises(PasswordPolicyError, match=needle):
        validate_password(password)


def test_min_length_constant_matches_policy() -> None:
    assert MIN_PASSWORD_LENGTH == 8

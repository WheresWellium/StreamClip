"""Single source of truth for password strength.

Registration, password change, and password reset all validate through
:func:`validate_password` so the policy can never drift between call sites.
Keep this module dependency-free so both the API schemas and the auth service
can import it cheaply.
"""

from __future__ import annotations

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
# bcrypt only hashes the first 72 bytes; anything longer gives a false sense of
# strength (the tail is silently ignored), so we reject it explicitly.
BCRYPT_MAX_BYTES = 72

# Small deny-list of well-known weak passwords that still pass a naive
# letter+digit check. Intentionally excludes strings used by the test suite.
_COMMON_PASSWORDS = frozenset(
    {
        "password",
        "password1",
        "passw0rd",
        "12345678",
        "123456789",
        "1234567890",
        "qwerty123",
        "qwertyuiop",
        "letmein1",
        "welcome1",
        "admin1234",
        "iloveyou1",
        "abc12345",
        "changeme1",
        "streamclip",
        "qclip1234",
    }
)


class PasswordPolicyError(ValueError):
    """Password failed the policy. The message is safe to show the user."""


def validate_password(password: str) -> None:
    """Raise :class:`PasswordPolicyError` if *password* is unacceptable."""
    if not isinstance(password, str) or not password:
        raise PasswordPolicyError("Password is required.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise PasswordPolicyError(
            f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
        )
    if len(password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise PasswordPolicyError(
            "Password is too long to hash securely; please shorten it."
        )
    has_letter = any(c.isalpha() for c in password)
    has_non_letter = any(not c.isalpha() for c in password)
    if not (has_letter and has_non_letter):
        raise PasswordPolicyError(
            "Password must include letters and at least one number or symbol."
        )
    if password.lower() in _COMMON_PASSWORDS:
        raise PasswordPolicyError(
            "That password is too common. Pick something harder to guess."
        )

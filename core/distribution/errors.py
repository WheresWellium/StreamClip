"""Distribution domain errors."""

from __future__ import annotations

from core.errors import StreamClipError


class DistributionProRequired(StreamClipError):
    def __init__(self) -> None:
        super().__init__(
            "Distribution requires Pro",
            user_message="Publishing and scheduling are Pro features. Activate a license in Settings.",
            code="PRO_REQUIRED",
            http_status=403,
        )


class ClipNotApprovedError(StreamClipError):
    def __init__(self) -> None:
        super().__init__(
            "Clip not approved",
            user_message="Approve this clip before publishing or saving to your vault.",
            code="NOT_APPROVED",
            http_status=400,
        )


class VaultFullError(StreamClipError):
    def __init__(self, limit: int) -> None:
        super().__init__(
            f"Vault limit {limit} reached",
            user_message=f"Your Clip Vault is full ({limit} clips). Remove clips from Vault to save more.",
            code="VAULT_FULL",
            http_status=400,
        )


class AlreadyInVaultError(StreamClipError):
    def __init__(self) -> None:
        super().__init__(
            "Clip already in vault",
            user_message="This clip is already in your Clip Vault.",
            code="ALREADY_IN_VAULT",
            http_status=409,
        )


class NoConnectionError(StreamClipError):
    def __init__(self, platform: str) -> None:
        label = platform.replace("_", " ").title()
        super().__init__(
            f"No connection for {platform}",
            user_message=f"Connect {label} in Distribution before publishing.",
            code="NO_CONNECTION",
            http_status=400,
        )


class PlatformNotEnabledError(StreamClipError):
    def __init__(self, platform: str) -> None:
        super().__init__(
            f"Platform {platform} not enabled",
            user_message="This platform is not available on this install.",
            code="PLATFORM_DISABLED",
            http_status=400,
        )


class VideoTooLongError(StreamClipError):
    def __init__(self, max_secs: float) -> None:
        super().__init__(
            f"Clip exceeds {max_secs}s",
            user_message=f"Clip exceeds the {int(max_secs)} second platform limit.",
            code="VIDEO_TOO_LONG",
            http_status=400,
        )


class DuplicateInFlightError(StreamClipError):
    def __init__(self, publish_job_id: str) -> None:
        super().__init__(
            "Publish already in flight",
            user_message="This clip is already publishing to that platform.",
            code="DUPLICATE_IN_FLIGHT",
            http_status=409,
        )
        self.publish_job_id = publish_job_id


class ClipNotReadyError(StreamClipError):
    def __init__(self) -> None:
        super().__init__(
            "Clip not ready",
            user_message="Clip must be fully rendered before publishing.",
            code="clip_not_ready",
            http_status=400,
        )

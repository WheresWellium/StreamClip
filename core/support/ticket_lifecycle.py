"""Bug report status transitions (TDD §13.1)."""

from __future__ import annotations

BUG_REPORT_STATUSES = frozenset({"open", "triage", "assigned", "resolved"})

_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "open": frozenset({"triage", "assigned", "resolved"}),
    "triage": frozenset({"open", "assigned", "resolved"}),
    "assigned": frozenset({"open", "resolved"}),
    "resolved": frozenset({"open"}),
}

_UNSET = object()
UNSET = _UNSET


class InvalidBugReportTransition(ValueError):
    """Raised when an admin attempts an illegal status change."""


def validate_status_transition(current: str, new_status: str) -> None:
    if new_status not in BUG_REPORT_STATUSES:
        raise InvalidBugReportTransition(f"Unknown status: {new_status}")
    allowed = _VALID_TRANSITIONS.get(current, frozenset())
    if new_status not in allowed:
        raise InvalidBugReportTransition(
            f"Cannot transition from {current!r} to {new_status!r}",
        )


def resolve_next_status(
    current: str,
    *,
    requested_status: str | None,
    assigned_to: str | None | object = _UNSET,
) -> str:
    """Derive the next status from an admin PATCH body."""
    if assigned_to is not _UNSET and assigned_to and requested_status is None:
        if current in {"open", "triage"}:
            validate_status_transition(current, "assigned")
            return "assigned"
    if requested_status is None:
        return current
    validate_status_transition(current, requested_status)
    return requested_status

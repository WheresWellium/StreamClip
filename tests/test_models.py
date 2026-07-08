"""Repository and model unit tests."""

from __future__ import annotations

from backend.db.models import ClipStatus, InstallOAuthApp, JobStatus, UserTier, _enum_values


def test_install_oauth_app_columns_match_migration_schema():
    """Regression: table 0006 has updated_at only — no created_at."""
    cols = {c.name for c in InstallOAuthApp.__table__.columns}
    assert cols == {
        "platform",
        "client_id",
        "client_secret_enc",
        "redirect_uri",
        "updated_at",
    }


def test_enum_values_match_postgres():
    assert _enum_values(JobStatus) == [
        "queued", "ingesting", "transcribing", "detecting",
        "processing", "done", "error", "cancelled",
    ]
    assert _enum_values(ClipStatus) == ["pending", "processing", "done", "error"]
    assert _enum_values(UserTier) == ["free", "pro", "admin"]

"""Focused coverage for backend/db/types.py dialect-portable helpers.

These are Alembic migration helpers that branch on `bind.dialect.name`.
We exercise both the postgresql and sqlite branches with lightweight fakes
instead of a real Alembic migration context.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from sqlalchemy.dialects.postgresql import JSONB

from backend.db import types as db_types


def _bind(dialect_name: str) -> SimpleNamespace:
    return SimpleNamespace(
        dialect=SimpleNamespace(name=dialect_name),
        execute=MagicMock(),
    )


def test_portable_json_load_dialect_impl_postgres_and_sqlite():
    col = db_types.PortableJSON()
    pg_dialect = SimpleNamespace(name="postgresql", type_descriptor=lambda t: t)
    sqlite_dialect = SimpleNamespace(name="sqlite", type_descriptor=lambda t: t)

    pg_impl = col.load_dialect_impl(pg_dialect)
    sqlite_impl = col.load_dialect_impl(sqlite_dialect)

    assert isinstance(pg_impl, JSONB)
    assert not isinstance(sqlite_impl, JSONB)


def test_portable_json_type_postgres_and_sqlite():
    assert isinstance(db_types.portable_json_type(_bind("postgresql")), JSONB)
    assert not isinstance(db_types.portable_json_type(_bind("sqlite")), JSONB)


def test_json_server_default_postgres_and_sqlite():
    pg_default = db_types.json_server_default("{}", _bind("postgresql"))
    sqlite_default = db_types.json_server_default("{}", _bind("sqlite"))

    assert "jsonb" in str(pg_default)
    assert "jsonb" not in str(sqlite_default)


def test_existing_pg_enum_and_portable_tier_enum():
    enum_type = db_types.existing_pg_enum("user_tier", "free", "pro", "admin")
    assert enum_type.name == "user_tier"

    pg_tier = db_types.portable_tier_enum(_bind("postgresql"))
    sqlite_tier = db_types.portable_tier_enum(_bind("sqlite"))
    assert pg_tier.name == "user_tier"
    assert sqlite_tier.length == 16


def test_drop_pg_enums_postgres_executes_and_sqlite_noop():
    pg_bind = _bind("postgresql")
    db_types.drop_pg_enums(pg_bind, "enum_a", "enum_b")
    assert pg_bind.execute.call_count == 2

    sqlite_bind = _bind("sqlite")
    db_types.drop_pg_enums(sqlite_bind, "enum_a")
    sqlite_bind.execute.assert_not_called()


def test_add_column_sqlite_uses_batch_mode():
    batch = MagicMock()
    op_mock = MagicMock()
    op_mock.batch_alter_table.return_value.__enter__.return_value = batch
    with patch.object(db_types, "op", op_mock):
        db_types.add_column(_bind("sqlite"), "jobs", MagicMock())
    batch.add_column.assert_called_once()


def test_add_column_postgres_uses_op_directly():
    op_mock = MagicMock()
    with patch.object(db_types, "op", op_mock):
        db_types.add_column(_bind("postgresql"), "jobs", MagicMock())
    op_mock.add_column.assert_called_once()


def test_alter_column_sqlite_uses_batch_mode():
    batch = MagicMock()
    op_mock = MagicMock()
    op_mock.batch_alter_table.return_value.__enter__.return_value = batch
    with patch.object(db_types, "op", op_mock):
        db_types.alter_column(_bind("sqlite"), "jobs", "status", nullable=True)
    batch.alter_column.assert_called_once_with("status", nullable=True)


def test_alter_column_postgres_uses_op_directly():
    op_mock = MagicMock()
    with patch.object(db_types, "op", op_mock):
        db_types.alter_column(_bind("postgresql"), "jobs", "status", nullable=True)
    op_mock.alter_column.assert_called_once_with("jobs", "status", nullable=True)


def test_create_foreign_key_sqlite_uses_batch_mode():
    batch = MagicMock()
    op_mock = MagicMock()
    op_mock.batch_alter_table.return_value.__enter__.return_value = batch
    with patch.object(db_types, "op", op_mock):
        db_types.create_foreign_key(
            _bind("sqlite"), "fk_jobs_owner", "jobs", "users", ["owner_id"], ["id"],
        )
    batch.create_foreign_key.assert_called_once_with(
        "fk_jobs_owner", "users", ["owner_id"], ["id"],
    )


def test_create_foreign_key_postgres_uses_op_directly():
    op_mock = MagicMock()
    with patch.object(db_types, "op", op_mock):
        db_types.create_foreign_key(
            _bind("postgresql"), "fk_jobs_owner", "jobs", "users", ["owner_id"], ["id"],
        )
    op_mock.create_foreign_key.assert_called_once_with(
        "fk_jobs_owner", "jobs", "users", ["owner_id"], ["id"],
    )

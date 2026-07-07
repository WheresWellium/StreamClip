"""
Dialect-portable SQLAlchemy types and Alembic migration helpers.

Postgres (Docker) keeps JSONB / native ENUM where applicable; SQLite (desktop)
uses JSON columns and string-backed enums.
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Connection
from sqlalchemy.types import TypeDecorator


class PortableJSON(TypeDecorator):
    """JSONB on PostgreSQL, plain JSON on SQLite and other dialects."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


def portable_json_type(bind: Connection) -> Any:
    """Column type for JSON payloads in Alembic migrations."""
    if bind.dialect.name == "postgresql":
        return JSONB()
    return sa.JSON()


def json_server_default(value: str, bind: Connection) -> sa.TextClause:
    """Portable JSON literal default (object/array) for migrations."""
    if bind.dialect.name == "postgresql":
        cast = "jsonb" if isinstance(portable_json_type(bind), JSONB) else "json"
        return sa.text(f"'{value}'::{cast}")
    return sa.text(f"'{value}'")


def existing_pg_enum(name: str, *values: str) -> Any:
    """Reference an existing PostgreSQL ENUM type (create_type=False)."""
    return PG_ENUM(*values, name=name, create_type=False)


def portable_tier_enum(bind: Connection) -> Any:
    """user_tier column type — native ENUM on Postgres, string on SQLite."""
    values = ("free", "pro", "admin")
    if bind.dialect.name == "postgresql":
        return existing_pg_enum("user_tier", *values)
    return sa.String(16)


def drop_pg_enums(bind: Connection, *names: str) -> None:
    """DROP TYPE only on PostgreSQL (no-op on SQLite)."""
    if bind.dialect.name != "postgresql":
        return
    for name in names:
        bind.execute(sa.text(f"DROP TYPE IF EXISTS {name}"))


def add_column(bind: Connection, table_name: str, column: sa.Column) -> None:
    """Add a column; uses batch mode on SQLite when constraints are present."""
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table_name) as batch:
            batch.add_column(column)
    else:
        op.add_column(table_name, column)


def alter_column(bind: Connection, table_name: str, column_name: str, **kwargs: Any) -> None:
    """Alter a column; uses batch mode on SQLite."""
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table_name) as batch:
            batch.alter_column(column_name, **kwargs)
    else:
        op.alter_column(table_name, column_name, **kwargs)


def create_foreign_key(
    bind: Connection,
    constraint_name: str,
    source_table: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
    **kwargs: Any,
) -> None:
    """Create FK; uses batch mode on SQLite."""
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(source_table) as batch:
            batch.create_foreign_key(
                constraint_name,
                referent_table,
                local_cols,
                remote_cols,
                **kwargs,
            )
    else:
        op.create_foreign_key(
            constraint_name,
            source_table,
            referent_table,
            local_cols,
            remote_cols,
            **kwargs,
        )

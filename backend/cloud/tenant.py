"""Multi-tenant cloud deployment context (stub)."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Annotated

from fastapi import Header

_tenant_id: ContextVar[str | None] = ContextVar("tenant_id", default=None)


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str | None


def get_current_tenant_id() -> str | None:
    return _tenant_id.get()


def set_current_tenant_id(tenant_id: str | None) -> None:
    _tenant_id.set(tenant_id)


async def tenant_from_header(
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
) -> TenantContext:
    set_current_tenant_id(x_tenant_id)
    return TenantContext(tenant_id=x_tenant_id)

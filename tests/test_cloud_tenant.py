"""Multi-tenant cloud stub — header → context var."""

from __future__ import annotations

from backend.cloud import tenant


async def test_tenant_from_header_sets_context():
    ctx = await tenant.tenant_from_header(x_tenant_id="tenant-a")
    assert ctx.tenant_id == "tenant-a"
    assert tenant.get_current_tenant_id() == "tenant-a"


async def test_tenant_from_header_none_clears():
    await tenant.tenant_from_header(x_tenant_id="tenant-b")
    ctx = await tenant.tenant_from_header(x_tenant_id=None)
    assert ctx.tenant_id is None
    assert tenant.get_current_tenant_id() is None


def test_set_current_tenant_id_direct():
    tenant.set_current_tenant_id("direct")
    assert tenant.get_current_tenant_id() == "direct"
    tenant.set_current_tenant_id(None)

"""API contract tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_ok(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert "database" in body


@pytest.mark.asyncio
async def test_create_job_requires_source(client):
    resp = await client.post("/api/jobs", json={"target_clips": 1})
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_source"


@pytest.mark.asyncio
async def test_metrics_endpoint(client):
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "streamclip_requests_total" in resp.text


@pytest.mark.asyncio
async def test_process_time_header(client):
    resp = await client.get("/api/health")
    assert "x-process-time" in {k.lower() for k in resp.headers}


@pytest.mark.asyncio
async def test_meta_endpoint(client):
    resp = await client.get("/api/meta")
    assert resp.status_code == 200
    assert "caption_styles" in resp.json()

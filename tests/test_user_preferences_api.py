"""User preferences API (TDD §16)."""

from __future__ import annotations

import uuid

import pytest

from backend.api.schemas import UserPreferencesOut, UserPreferencesUpdateRequest


def test_user_preferences_out_defaults():
    out = UserPreferencesOut.from_storage({})
    assert out.memory_enabled is False
    assert out.title_style == "gaming"
    assert out.vocabulary == []


def test_user_preferences_update_request_patch():
    body = UserPreferencesUpdateRequest(
        memory_enabled=True,
        vocabulary=["Ace", "clutch", "Ace"],
        title_style="promo",
    )
    patch = body.as_patch()
    assert patch["memory_enabled"] is True
    assert patch["vocabulary"] == ["Ace", "clutch"]
    assert patch["title_style"] == "promo"


def test_user_preferences_out_trims_lists():
    out = UserPreferencesOut.from_storage(
        {"vocabulary": ["  hot  ", "", "word"], "memory_enabled": True},
    )
    assert out.vocabulary == ["hot", "word"]
    assert out.memory_enabled is True


@pytest.mark.asyncio
async def test_user_preferences_roundtrip(client):
    email = f"prefs-{uuid.uuid4().hex[:10]}@example.com"
    reg = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "hunter2secure"},
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    initial = await client.get("/api/settings/preferences", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["memory_enabled"] is False

    updated = await client.put(
        "/api/settings/preferences",
        headers=headers,
        json={"memory_enabled": True, "title_style": "tip"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["memory_enabled"] is True
    assert body["title_style"] == "tip"

    wiped = await client.delete("/api/settings/preferences", headers=headers)
    assert wiped.status_code == 200
    assert wiped.json()["memory_enabled"] is False
    assert wiped.json()["vocabulary"] == []


@pytest.mark.asyncio
async def test_user_preferences_requires_auth(client):
    resp = await client.get("/api/settings/preferences")
    assert resp.status_code == 401

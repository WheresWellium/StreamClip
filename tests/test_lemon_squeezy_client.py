"""Tests for Lemon Squeezy License API client and checkout URLs."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from core.commerce.checkout_urls import build_ls_checkout_url
from core.commerce.lemon_squeezy_client import (
    activate_license_with_ls,
    validate_license_with_ls,
)


def test_build_ls_checkout_url_prefill():
    url = build_ls_checkout_url(
        "https://store.lemonsqueezy.com/checkout/buy/123",
        email="test@example.com",
        name="Test User",
    )
    assert "test" in url
    assert "checkout" in url


def test_build_ls_checkout_url_rejects_empty():
    with pytest.raises(ValueError):
        build_ls_checkout_url("")


@pytest.mark.asyncio
async def test_activate_license_with_ls_success():
    payload = {
        "activated": True,
        "license_key": {"status": "active"},
        "instance": {"id": "inst-1"},
        "meta": {
            "variant_id": 42,
            "order_id": 99,
            "customer_email": "buyer@example.com",
        },
    }
    response = httpx.Response(200, json=payload, request=httpx.Request("POST", "http://test"))

    with patch("core.commerce.lemon_squeezy_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=response)
        result = await activate_license_with_ls("KEY-1", "machine-a", api_key="secret")

    assert result.ok is True
    assert result.variant_id == "42"
    assert result.order_id == "99"
    assert result.customer_email == "buyer@example.com"


@pytest.mark.asyncio
async def test_activate_license_with_ls_failure():
    response = httpx.Response(
        200,
        content=json.dumps({"activated": False, "error": "invalid"}).encode(),
        request=httpx.Request("POST", "http://test"),
    )

    with patch("core.commerce.lemon_squeezy_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=response)
        result = await activate_license_with_ls("BAD", "machine-a", api_key="secret")

    assert result.ok is False
    assert result.error == "invalid"


@pytest.mark.asyncio
async def test_activate_license_without_api_key():
    result = await activate_license_with_ls("KEY", "m", api_key="")
    assert result.ok is False
    assert result.error == "api_key_unconfigured"


@pytest.mark.asyncio
async def test_validate_license_with_ls_success():
    response = httpx.Response(
        200,
        json={"valid": True, "license_key": {"status": "active"}},
        request=httpx.Request("POST", "http://test"),
    )

    with patch("core.commerce.lemon_squeezy_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=response)
        result = await validate_license_with_ls("KEY", "inst-1", api_key="secret")

    assert result.ok is True
    assert result.license_status == "active"

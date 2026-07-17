"""Lemon Squeezy checkout URL helpers for invite emails."""

from __future__ import annotations

from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse


def build_ls_checkout_url(
    base_url: str,
    *,
    email: str | None = None,
    name: str | None = None,
) -> str:
    """Append Lemon Squeezy checkout prefill query params to a checkout URL."""
    base = (base_url or "").strip()
    if not base:
        raise ValueError("checkout base URL is required")

    parsed = urlparse(base)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"invalid checkout URL: {base}")

    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if email:
        params["checkout[email]"] = email.strip()
    if name:
        params["checkout[name]"] = name.strip()

    query = urlencode(params, quote_via=quote)
    return urlunparse(parsed._replace(query=query))

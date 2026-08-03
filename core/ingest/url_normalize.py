"""Canonical source URL normalization for ingest and job creation."""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse

# Hosts we accept without an explicit scheme (user paste from browser bar).
_SCHEMELESS_HOST_PREFIXES = (
    "twitch.tv/",
    "www.twitch.tv/",
    "m.twitch.tv/",
    "clips.twitch.tv/",
    "kick.com/",
    "www.kick.com/",
    "youtube.com/",
    "www.youtube.com/",
    "youtu.be/",
    "tiktok.com/",
    "www.tiktok.com/",
    "vm.tiktok.com/",
)


def normalize_source_url(raw: str) -> str:
    """
    Normalize a pasted source URL to a stable https form.

    Handles missing schemes, mobile Twitch hosts, and strips tracking query
    params on Twitch VOD URLs (they do not affect download identity).
    """
    url = raw.strip()
    if not url:
        raise ValueError("source_url is empty")

    lower = url.lower()
    if not lower.startswith(("http://", "https://")):
        if not any(lower.startswith(p) or lower == p.rstrip("/") for p in _SCHEMELESS_HOST_PREFIXES):
            raise ValueError("source_url must start with http:// or https://")
        url = f"https://{url.removeprefix('www.')}" if lower.startswith("www.") else f"https://{url}"

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError("source_url must include a host")

    # Preserve explicit http:// (direct media / local fixtures). Only schemeless
    # pastes above are upgraded to https.
    scheme = parsed.scheme.lower() if parsed.scheme else "https"
    if scheme not in ("http", "https"):
        raise ValueError("source_url must start with http:// or https://")
    if host == "m.twitch.tv":
        host = "www.twitch.tv"

    path = parsed.path or "/"
    query = parsed.query
    # VOD identity is path-only; query params are UI filters (e.g. ?filter=archives).
    if host in ("twitch.tv", "www.twitch.tv") and "/videos/" in path.lower():
        query = ""

    netloc = host
    if parsed.port and parsed.port not in (80, 443):
        netloc = f"{host}:{parsed.port}"

    return urlunparse((scheme, netloc, path, "", query, ""))

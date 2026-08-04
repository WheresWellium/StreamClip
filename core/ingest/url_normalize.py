"""Canonical source URL normalization for ingest and job creation."""

from __future__ import annotations

import re
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

_TWITCH_VOD_PATH = re.compile(r"^/videos/\d+/?$", re.IGNORECASE)
_TWITCH_CHANNEL_CLIP = re.compile(r"^/[^/]+/clip/[^/]+/?$", re.IGNORECASE)
_TWITCH_LIVE_MSG = (
    "That looks like a Twitch channel or listing page, not a downloadable VOD. "
    "Open the video -> Share -> copy the twitch.tv/videos/... link, or upload the file."
)


def _reject_unsupported_twitch(host: str, path: str) -> None:
    """Reject channel home / video listings; allow VOD ids and clips only."""
    if host == "clips.twitch.tv":
        slug = path.strip("/")
        if not slug or "/" in slug:
            raise ValueError(
                "That Twitch clip link looks incomplete. Paste a full clips.twitch.tv/… URL."
            )
        return

    if host not in ("twitch.tv", "www.twitch.tv"):
        return

    normalized = path.rstrip("/") or "/"
    if _TWITCH_VOD_PATH.match(normalized) or _TWITCH_CHANNEL_CLIP.match(normalized):
        return

    # /videos without id, /videos?filter=highlights, bare /{channel}, /{channel}/videos, …
    raise ValueError(_TWITCH_LIVE_MSG)


def normalize_source_url(raw: str) -> str:
    """
    Normalize a pasted source URL to a stable https form.

    Handles missing schemes, mobile Twitch hosts, and strips tracking query
    params on Twitch VOD URLs (they do not affect download identity).
    Rejects Twitch channel/live home and highlight listing pages — qClip needs
    a concrete ``/videos/{id}`` or clip URL (or a file upload).
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

    _reject_unsupported_twitch(host, path)

    netloc = host
    if parsed.port and parsed.port not in (80, 443):
        netloc = f"{host}:{parsed.port}"

    return urlunparse((scheme, netloc, path, "", query, ""))

# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-08-03 (beta.20 font fallback + publish)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | beta.20 publish | — | ASS persist + caption font fallback |

## Pass rule (packaged evidence only)

Render: job `done` + dims + `captions_done` + ASS Fontname (or fallback) + OS font in preferred/fallback chain + crop diverge (P0-all).

## Shipped on master

- `5ffc498` — render claims harden, support-ingest, clip UX, http URL preserve
- Caption font fallback (`resolve_caption_fontname`) for Helvetica Neue / SF Pro / Arial Rounded
- Version bumped to **1.0.0-beta.20** (publish in flight / next)

## Still open

Finish `publish_desktop_release.ps1` for beta.20; re-smoke hardened P0; henna SMTP secrets; TikTok IP; EV signing; clean VM.

## Download

Latest target → **1.0.0-beta.20**  
https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe

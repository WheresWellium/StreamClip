# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-08-03 (beta.20 shipped + hardened P0 Pass)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | idle / next open items | — | — |

## Pass rule (packaged evidence only)

Render: job `done` + dims + `captions_done` + ASS Fontname (preferred or fallback) + OS font chain + crop diverge (P0-all).

## Shipped

- `5ffc498` render claims / support-ingest / clip UX
- `5174abb` caption font fallback + beta.20 bump
- Release **v1.0.0-beta.20** published (unsigned, 521 MB)

## Render matrix (beta.20 packaged) — P0 Pass

| Cell | Result |
|------|--------|
| P0-gaming | Pass Impact, crop 291x517 |
| P0-irl | Pass Impact, crop 405x720 |
| P0-landscape | Pass Arial fallback (Helvetica Neue missing), scale_only |
| P0-all diverge | Pass gaming != irl |

## Still open

Henna SMTP secrets for F13; TikTok IP; EV signing; clean-VM install→first-clip.

## Download

Latest → **1.0.0-beta.20**  
https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe

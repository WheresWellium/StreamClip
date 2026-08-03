# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-08-03 (render matrix harden)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | render claim harden | — | `scripts/smoke_render_matrix.ps1` |

## Pass rule (packaged evidence only)

Render: job `done` + ffprobe WxH + `captions_done` (not `no_words`) + `*_captioned.mp4` + ASS Fontname or log `fontname=` + OS font installed + reframe `crop_window`/`scale_only` + no `boxblur`/`letterbox` in default path. P0-all: gaming crop != irl crop.

## Source matrix (beta.19) — done

Pass: upload-video/audio, twitch-vod, kick, youtube, direct-https. Fail: tiktok (IP block).

## Render matrix (hardened) — P0 Fail (real catches)

| Cell | Status | Why |
|------|--------|-----|
| P0-gaming | Fail | `ass_not_persisted` (beta.19 deletes ASS; keep-ASS not in exe yet) |
| P0-irl | Fail | same; crop was 405x720 vs gaming 291x517 (diverge OK) |
| P0-landscape | Fail | OS missing **Helvetica Neue** for `minimal_white` |

Prior soft Pass was false positive (sine fixture → `no_words_in_clip_window`). Speech fixture now in harness.

## Code landed (needs desktop republish for ASS assert)

- `core/captions.py` persist `*_captioned.ass` + log `fontname=`
- `core/reframe.py` docstring: centre-crop fallback (not letterbox)
- `tests/test_render_claim_guards.py` (6 unit tests green)

## Still open

Republish sidecar for ASS Fontname Pass; desktop font map/fallback for Helvetica Neue / SF Pro / Arial Rounded; F13 henna SMTP; TikTok IP; EV signing; clean VM.

## Download

Latest → **1.0.0-beta.19**  
https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe

# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-27

## Active chats

| Chat | Branch | Focus |
|------|--------|-------|
| cloud-agent | `cursor/cinematic-loading-screen-f921` | Cinematic app loading screen |

## Current focus

**Cinematic boot loader:** Modular `web/components/loading-screen/*` integrated via `SidecarReadyGate`. Original cover art at `web/public/brand/loading-cover.svg`.

## Blockers

- EV Authenticode cert (§4.10) — SmartScreen warns until signed.
- macOS DMG + notarization (§5.2–5.3) — Mac host + Apple Developer.

## Validation

- Coverage ✅ 96.08% (unrelated)
- Web typecheck / lint / build — pending this branch

## Next steps

1. Finish loading-screen implementation + SidecarReadyGate integration.
2. Unit tests for lifecycle/config; Playwright smoke for boot copy.
3. typecheck / lint / build; push PR.

## Key paths

- Loader: `web/components/loading-screen/`
- Gate: `web/components/layout/sidecar-ready-gate.tsx`
- Cover: `web/public/brand/loading-cover.svg`

# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-28 (beta.6 published + cohort re-email sent)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `master` | Phase 0 monitor | — | `v1.0.0-beta.6` Latest; docs cleanup |

## Readiness

| Metric | % | Notes |
|--------|---|-------|
| Tester-ready **shipped** | **~85%** | beta.6 installer live; W2/W3/W4/G4 shipped |
| Phase 0 **exit** | **~65%** | O4/O5/O11/O14 human ops remain |

## Shipped (2026-07-28)

| Item | Status |
|------|--------|
| PR #10 + #11 | ✅ merged |
| beta.6 Windows installer (O12) | ✅ [release](https://github.com/WheresWellium/StreamClip/releases/tag/v1.0.0-beta.6) |
| Cohort re-email (Win + Mac) | ✅ 8/8 sent |
| Claim / license seed / install secrets / CPU config | ✅ in beta.6 |

## Blockers (human-only)

- O4 — cohort exit evidence · O5 — on-call names · O11 — EV signing · O14 — public Mac `.dmg`

## Next steps

1. Fill `BETA_COHORT_EXIT.md` as testers report (O4).
2. Fill on-call tokens in `BETA_ON_CALL.md` (O5).
3. Mac testers: Docker path only until O14.

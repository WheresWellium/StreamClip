# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-28 (beta.6 delivery branch ready)

## Active chats

| Branch | Task | Lock id | Paths / notes |
|--------|------|---------|----------------|
| `beta6-delivery` | Post-PR #9 beta.6 slice | — | 3 commits atop `origin/master`; open PR → O12 |

## Readiness

| Metric | % | Notes |
|--------|---|-------|
| Tester-ready **local** (tree) | **~85%** | G4+W2+W3+W4; desktop tests 23/23; tsc clean |
| Tester-ready **shipped** (master/beta.5) | **~60%** | needs beta.6 publish |
| Phase 0 **exit** | **~62%** | O4/O5/O11/O14 human ops remain |

**Merge-ready:** yes — clean 3-commit stack on `origin/master`.

## P0 slice (this delivery)

| Item | Status |
|------|--------|
| G4 claim-device SQLite fix | ✅ |
| W2 cohort license seed | ✅ |
| W3 per-install secrets | ✅ |
| W4 CPU throughput config | ✅ |
| Web modal/warmup/format | ✅ |
| O12 beta.6 installer | ⏳ operator |

## Blockers (human-only)

- O12 — `scripts/publish_desktop_release.ps1` after merge; bump `docs/BETA_DOWNLOAD.md`
- O5 — on-call tokens · O4 — evidence pack · O11 — code signing · O14 — Mac `.dmg`

## Next steps

1. Open PR from `beta6-delivery`; merge to master.
2. Publish beta.6; optional cohort re-send (`tmp/tester-reply-draft.txt`).

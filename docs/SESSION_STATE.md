# Session state (compaction anchor)

**Purpose:** Single source of truth when conversation is summarized. Keep ≤60 lines.
**Last updated:** 2026-07-07 (pushed master; beta kit + prod secrets verifier)

## Current focus

**Phase 0 invite path:** coverage GREEN (95.40%), stack smoke GREEN on dev machine. Agent shipped `prepare_beta_kit.ps1`, `verify_production_secrets.ps1`, prod compose metrics/rate-limit wiring. **User blocker:** §3.8 clean-VM verify.

## Blockers

- §3.8 clean-VM `verify_stack.ps1` — runbook `docs/CLEAN_VM_VERIFY.md` (user, fresh Win11 VM)
- GHCR images (§8.8): tag release + publish if testers use prod compose without `--build`
- OAuth redirect URIs (§8.13): match deployed `WEB_ORIGIN` in Google/TikTok consoles

## Next steps (ordered)

1. User: clean-VM verify per `docs/CLEAN_VM_VERIFY.md`
2. User: `.\scripts\prepare_beta_kit.ps1` → send zip or repo access to waitlist
3. User: fill `.env.production` + `verify_production_secrets.ps1` before any public host
4. Optional: `git tag v0.1.0-beta.1` + push to trigger GHCR workflow

## Key paths

- Push: `origin/master` @ GitHub WheresWellium/StreamClip
- Kit: `scripts/prepare_beta_kit.ps1` → `dist/streamclip-beta-kit-*.zip`
- Secrets: `scripts/verify_production_secrets.ps1`, `.env.production.example`
- Gates: `scripts/verify_coverage.ps1`, `scripts/verify_stack.ps1`
- Truth: `docs/MASTER_TODO.md` §3.8, §8.9, `docs/BETA_GO_LIVE.md`

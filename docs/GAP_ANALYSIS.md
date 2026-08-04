# StreamClip Gap Analysis

**Last run:** 2026-08-04 (revision 16 — matrix + e2e honesty)

### Revision 16 — matrix timing + full e2e gaps (2026-08-04)

Post-run audit of the 180-cell create-option pipeline timing matrix and Playwright full e2e. Claims of “matrix green” / “full e2e green” were directionally right but underspecified.

| ID | Gap | Sev | Fix | Status |
|----|-----|-----|-----|--------|
| T80 | Matrix “green” read as N clips per cell; 75% (135/180) had `clip_count < target_clips` on short fixture | **P1** | code+doc | **Fixed** — summarize reports `pipeline_green` vs `target_clips_green` / `clips_short_of_target`; `--require-target-clips`; done requires `clip_count>=1`; evidence + tests |
| T81 | `verify_stack -RunE2E` / CI only ran happy-path; ui-journey + `E2E_API_BASE` unwired | **P1** | test | **Fixed** — `-RunE2E` → `run_e2e_full.ps1`; CI runs ui-journey then happy-path with `E2E_API_BASE` |
| T82 | CONTRIBUTING / release gate silent on new runners | P2 | doc | **Fixed** — CONTRIBUTING e2e+matrix commands; `verify_desktop_release` optional recheck lines |
| T83 / U27 | “Full Playwright upload→clips” still deferred; prior wording conflated with smoke | P2 | doc | **Clarified** — mock journey + live API smoke = ship bar; live browser upload→GPU→playable clip remains deferred |
| T84 | Rev 16 briefly reused T70–T72 IDs already assigned to a11y/validation rows | P2 | doc | **Fixed** — renumbered matrix/e2e rows to T80–T83 |
| O4d | Clean-VM install→first-clip | P0 | ops | **Still open** |
| O11 | EV / SmartScreen | P1 | ops | **Still open** |
| O14b | Mac notarization / universal DMG | P2 | ops | **Still open** |

**Net:** matrix remains **pipeline_green** (180/180 create→done ≥1 clip); not target-clips green on smoke fixture. Full e2e host path is now the documented/CI bar. Residue still operator: O4d / O11 / O14b.

### Revision 15 — create → live job navigation (2026-08-03)

Friend report on **v1.0.0-beta.23**: file upload + gaming + 16:9 + 1 clip → **home shell** after Generate clips; job still processing under Jobs. Root causes: SPA home fallback for `/jobs/*` misses, async create effect cancel race, trailing-slash mismatch vs `trailingSlash: true`.

| ID | Gap | Sev | Fix | Status |
|----|-----|-----|-----|--------|
| U78 | Create job lands on home instead of live overview | **P1** | code | **Closed in beta.24** — `afterCreateJobSuccess` + trailing-slash paths; `static_ui` jobs-miss ≠ home; build guards; matrix tests |
| U79 | Clip count ignored when **More options** collapsed | **P1** | code | **Closed in beta.24** — always-submit hidden `target_clips` |
| D14 | Henna how-to said **Submit**; UI says **Generate clips** | P2 | doc | **Fixed** — `docs/index.md` step 3 |
| O11 | Windows EV signing / SmartScreen | P1 | ops | **Still open** — beta.24 unsigned |
| O4d | Clean-VM install→first-clip operator sign-off | P0 | ops | **Still open** |
| O14b | Universal Mac DMG + notarization | P2 | ops | **Still open** |

**Net:** U78 + U79 ship in **beta.24**. Create-option matrix **pipeline_green** 180/180 (evidence: [`matrix-pipeline-timing-beta24.md`](evidence/matrix-pipeline-timing-beta24.md); see rev 16 / T80 for target-clips honesty). Full Playwright e2e **green** (ui-journey 23 + happy-path 12; [`e2e-full-beta24.md`](evidence/e2e-full-beta24.md); CI wiring T81). Residue remains operator: EV (O11), clean-VM (O4d), notarization (O14b).

**Desktop seams re-verified ok:** sidecar `verify_writable` fail-fast; `_writable_slots`; F13 henna support-ingest; virality heuristic fallback; `task_dispatch` on create; “Completed with errors”; `verify_desktop_release.ps1`.

### Revision 14 — Mac parity (2026-08-03)

| ID | Gap | Sev | Fix | Status |
|----|-----|-----|-----|--------|
| O14 | Mac DMG stuck on beta.6 while Windows on beta.22 | P1 | ops/ci | **Closed** — GHA `STREAMCLIP_MAC_SINGLE_ARCH=arm64` uploads `qClip-mac-arm64.dmg` to **v1.0.0-beta.22**; henna/docs on Latest |
| O14b | Universal Mac DMG + notarization | P2 | ops | **Still open** — local Mac Rosetta path; Apple Developer ID |

### Revision 13 — distribute-ready cut (2026-08-03)

| ID | Gap | Sev | Fix | Status |
|----|-----|-----|-----|--------|
| O13 | Legacy `N8N_OPS_WEBHOOK_URL` env alias | P2 | code | **Closed** |
| U77 | Clip card preview hardcoded 9:16 | P2 | code | **Closed** |
| O11 | Windows EV signing / SmartScreen | P1 | ops | **Still open** — beta.22 unsigned until cert |
| O4d | Clean-VM install→first-clip operator sign-off | P0 | ops | **Still open** |
| U27 | Playwright full live-stack journey | P2 | test | Defer |

### Revision 12 — beta.21 polish verification (2026-08-03)

| ID | Gap | Sev | Fix | Status |
|----|-----|-----|-----|--------|
| U73 | Partial fail SSE toasted “Job complete” | **P1** | code | **Fixed** — honest terminal SSE + amber UI |
| U74 | `jobDone` blocked Edit on job `error` | **P1** | code | **Fixed** — `done\|error` editable |
| U75 | Regenerate no auto-refresh | P2 | code | **Fixed** |
| U76 | Pan/zoom dirty banner dishonest | P2 | code | **Fixed** |
| D12 | Known-issues version drift | P2 | doc | **Fixed** |

**Net:** code P1s closed; Latest should be **beta.22**. Residue: EV cert + clean-VM + cohort numbers (operator).

---

### Revision 11 — desktop-first mastery audit (2026-07-31)

Re-centered the gap lens on the **product = the installer** (not Docker). Full architecture + seam audit from code; decision **harden, not rewrite** (TDD Appendix C). New truth docs: [`TECHNICAL_DESIGN.md`](TECHNICAL_DESIGN.md) Rev 5 (desktop-primary; Docker → Appendix D), [`DESKTOP_FAILURE_TAXONOMY.md`](DESKTOP_FAILURE_TAXONOMY.md) (F1–F12), [`CLEAN_DESKTOP_VM_VERIFY.md`](CLEAN_DESKTOP_VM_VERIFY.md), [`DESKTOP_UPGRADE_MATRIX.md`](DESKTOP_UPGRADE_MATRIX.md).

| ID | Gap (desktop-primary) | Sev | Fix | Status |
|----|-----------------------|-----|-----|--------|
| D1 | Writable check was **log-only** → sidecar booted into a guaranteed 500 / white screen (F1) | P0 | code | **Fixed** — `SystemExit(1)` with actionable message in `desktop_sidecar/run.py`; regression `test_run_server_exits_when_data_dirs_unwritable` |
| D2 | TDD/CLEAN_VM/README treated Docker as canonical while the exe is the product (F11) | P0 | doc | **Fixed** — TDD Rev 5 desktop-primary, README hero leads with installer, Docker demoted to Appendix D |
| D3 | No product ship gate — Docker clean-VM proved compose, not the `.exe` | P0 | ops/code | **Fixed** — `CLEAN_DESKTOP_VM_VERIFY.md` + `scripts/verify_desktop_clean.ps1` (fresh-data-dir boot smoke) |
| D4 | Desktop seam excluded from coverage (`-m "not desktop"` waiver, F10) | P1 | test | **Fixed** — `scripts/verify_desktop_coverage.ps1` measures the seam at **91%** (gate floor 85), wired into `verify_desktop.ps1` |
| D5 | Upgrade path (old build → new) untested (F5) | P1 | test | **Fixed** — `scripts/verify_desktop_upgrade.ps1` (old-rev DB → boot → data + licenses preserved; passes 0012→head) + manual matrix |
| D6 | BETA_KNOWN_ISSUES stale at beta.6 | P2 | doc | **Fixed** — beta.7; white-screen row added |
| D7 | First-run model failure copy (disk/network/AV) still generic (F6) | P1 | code | **Fixed** — `classify_failure`/`failure_hint`/`retry_prefetch`; `/api/health/models` +`failed`/`hint` + `POST …/retry`; `ModelWarmupBanner` failed state + Retry; 17 tests |
| D8 | Supervise UX (F4) | — | — | **Fixed + proven** — `failure-reason.ts` extracted (6 node tests); sidecar boot failures propagate non-zero (`test_run_server_propagates_boot_failure_nonzero`) |
| D9 | EV signing / SmartScreen (F9) | P1 | ops | **Tooling done** — `publish_desktop_release.ps1 -RequireSigned` + `verify_desktop_release.ps1 -RequireSigning` + [DESKTOP_SIGNING.md](DESKTOP_SIGNING.md); **blocked on operator EV cert purchase (O11)** — rechecked 2026-08-03 (`CSC_THUMBPRINT` unset; beta.20 unsigned Latest) |
| D11 | ~~**Desktop feedback black hole (F13)**~~ | **P0** | code+infra | **CLOSED 2026-08-03** — henna `api/support-ingest` + Vercel SMTP + packaged `OPS_WEBHOOK_URL` (MASTER §4.22) |
| D10 | Beta program still validated Docker, not the installer | P0 | doc | **Fixed** — [DESKTOP_COHORT_EXIT.md](DESKTOP_COHORT_EXIT.md) + MASTER §8.16d merge Phase0/Phase2; invite email rewritten for installer; Docker retained as Pro-only |

**Net:** all desktop P0s and code P1s closed. Residue is **operator-only**: EV cert purchase (D9/O11), clean-VM install→first-clip sign-off, cohort numbers (DESKTOP_COHORT_EXIT). Pipeline untouched — performance-first + minimize-work held. Turnkey gate: `.\scripts\verify_desktop_release.ps1` (green).

---

**Prior run:** 2026-07-28 (revision 10 — full dual-track audit: 23-claim technical matrix + 30-row UX sweep)

### Audit snapshot (2026-07-28 — Phase 0 exit strategic)

Strategic gap audit (desktop tester path + exit gates): **`tmp/gap-analysis-audit-2026-07-28.md`**.  
**Shipped (2026-07-28):** W2/W3/W4/G4 + **v1.0.0-beta.6** installer + cohort re-email 8/8.  
**Readiness ~90% shipped / ~70% Phase 0 exit.** Remaining: O4 cohort evidence, O5 on-call names, O11 EV signing. O14 Mac `.dmg` **published** (unsigned arm64 on beta.6).

## Executive summary

**Product = desktop installer** (Latest **v1.0.0-beta.24** Win + Mac arm64). Pipeline, F13, U78/U79, matrix **pipeline_green**, and Playwright mock+API smoke are in good shape (rev 16 honesty pass). Remaining blockers are **operator-only**: clean-VM (O4d), EV (O11), Mac notarization (O14b), cohort numbers. Live browser upload→clips e2e still deferred (U27).

### Open register (2026-07-28)

| ID | Gap | Sev | Fix | Status |
|----|-----|-----|-----|--------|
| O1 | `BETA_GO_LIVE` invites Blocked vs SENT | P0 | doc | **Fixed** this revision |
| O2 | `BETA_DOWNLOAD` table still beta.2 | P1 | doc | **Fixed** this revision |
| O3 | Quickstart missing `import_invite_license` | P1 | doc | **Fixed** this revision |
| O4 | Cohort H+2/H+24/H+72 + T0 exit evidence | P0 | ops | Tooling ✅ `scripts/capture_phase0_evidence.ps1` + `docs/evidence/` — ☐ operator runs T0…H72 + fills OPERATOR FILL in [`BETA_COHORT_EXIT.md`](BETA_COHORT_EXIT.md) |
| O5 | On-call roles TBD | P0 | ops | Scaffold ✅ placeholders `<PRIMARY_ONCALL_NAME>` etc. in [`BETA_ON_CALL.md`](BETA_ON_CALL.md) §1 + exit pack — ☐ operator fills real names (2 min; do not invent) |
| O6 | Invite pack email bodies vs keys.csv freshness | P0 | ops | **Verify PASS** (2026-07-27) — 8/8 match; re-send pack `tmp/phase0-invite-pack-resend/` · `tmp/invite-pack-status.md`; do not re-issue keys; send still user-gated |
| O7 | Ops alerting channel unconfigured | P1 | ops/code | **Closed via SMTP-only path** (2026-07-28) — no third-party connector. Resend SMTP live **PASS** from `api` + `worker` (`scripts/verify_smtp_alerting.ps1`); `job_failed`/`stack_degraded` now fall back to email via `deliver_ops_event`. `OPS_WEBHOOK_URL` optional. |
| O8 | Weak default AUTH secret (length not warned) | P1 | code | **Fixed** — non-dev settings reject missing/placeholder/short secrets; dev startup logs redacted `SECURITY_WARNING`; `tests/test_auth_secret_strength.py` |
| O9 | No seat-release UX (max 3 activations) | P1 | code | **Fixed** — Settings → License seat list/release + confirm; migration `0012_license_activation_seats` applied (head); same-machine activate upserts one seat row |
| O10 | Revoke ≠ jti blocklist for entitlement JWT | P1 | code | **Fixed** — `revoke_entitlement_hash` + verify check (`core/licensing.py`); admin revoke writes Redis/in-process set; `tests/test_licensing_blocklist.py` |
| O11 | Windows EV signing / SmartScreen | P1 | ops | Tooling ✅ [`DESKTOP_SIGNING.md`](DESKTOP_SIGNING.md) Paths A–D — ☐ buy/install cert (MASTER §4.10); **beta.20 remains unsigned** (2026-08-03) |
| O12 | Loader / desktop publish | P1 | ops | **Closed 2026-07-28** — `v1.0.0-beta.6` published; UI journey e2e green (`test:e2e:ui-journey`) |
| O13 | Deprecated job publish route; N8N env alias | P2 | code | Defer |
| O14 | macOS DMG + notarization | P2 | ops | arm64 on **beta.22** Latest ✅ (rev 14); ☐ universal upload; ☐ notarization |
| O15 | GAP / 110% Phase 1 coverage stretch | P2 | test | Defer — not Phase 0 blocker |

### New gaps from revision 10 audit (2026-07-28)

| ID | Gap | Sev | Fix | Evidence |
|----|-----|-----|-----|----------|
| T60 | Onboarding first-job trap — sample job redirect to `/jobs/{id}` fires before onboarding cookie set; middleware bounces user back to wizard step 1, job orphaned from view | **P0** | code | **Fixed** — `CreateJobForm.onJobCreated` marks onboarding complete before navigate (`create-job-form.tsx`, `onboarding-wizard.tsx`) |
| T61 | API-down handling inconsistent — `/jobs/new` + `/onboarding` hang on infinite "Loading…" (no `.catch` on `metaApi.meta()`); vault shows fake-empty; destinations drawer shows misleading "Connect platforms"; jobs list leaks raw "Failed to fetch" | P1 | code | **Fixed** — retryable error states on jobs/new + onboarding; vault loadError; distribution `loadError` + sign-in vs Pro copy |
| T62 | Stalled-job UX absent — worker death w/o terminal SSE event = eternal spinner; poll errors swallowed | P1 | code | **Fixed** — `useJobProgress.stalled` after 3 min / 3 poll failures; LiveProgress amber notice |
| T63 | `jobs/[id]/not-found.tsx` dead code — clients silently `router.replace("/jobs")` on 404 | P1 | code | **Fixed** — overview + clips clients render not-found UI in place |
| T64 | Token refresh only on window focus; `clearAuthTokens()` on any non-OK (incl. 5xx) → silent logout | P1 | code | **Fixed** — clear tokens only on 401/403 (`token-refresh.tsx`) |
| T65 | `caption.refine_clip_transcript: true` default = N per-clip Whisper passes, contradicting "single full transcribe" perf headline | P1 | code/doc | **Doc** — config.yaml comment documents throughput tradeoff (default kept for caption sync) |
| T66 | E2E is smoke-only, gated `E2E_RUN=1`; zero UI coverage of create→review→publish journey | P1 | test | **Fixed** — mock-API Playwright suite: `journey-create-review` + `failure-paths` + `onboarding-first-run` (23/23 PASS); helpers in `web/e2e/support/mock-api.ts`; run via `npm run test:e2e:ui-journey` (web on :3000 only; no GPU). Live-stack smoke remains `E2E_RUN=1`. |
| T67 | Dead config keys: `export.two_pass`, `licensing.public_key_pem`, `observability.metrics_port` | P2 | code | **Fixed** — removed unused fields |
| T68 | Entitlement JWTs signed with symmetric `auth.secret_key`; planned asymmetric signing never landed (dead `public_key_pem`) | P2 | code | Accepted — `public_key_pem` removed; O10 blocklist shipped for revoke |
| T69 | README documents 5 reframe presets + auto; code ships 9 (4 undocumented) | P2 | doc | **Fixed** — README preset table lists all 9 |
| T70 | Modals lack focus traps; `ClaimDeviceModal` missing `role="dialog"`; misc a11y (aria-pressed/aria-expanded on create form toggles; drawer tabs icon-only on mobile) | P2 | code | **Fixed** — dialog roles, Escape, aria-pressed/expanded/label; full focus-trap deferred |
| T71 | Anonymous user shown "Publishing requires Pro" when real blocker is sign-in; schedule datetime allows past dates | P2 | code | **Fixed** — sign-in branch + `min` on datetime-local |
| T72 | Field-level zod validation errors returned but never rendered (generic "Validation failed") | P2 | code | **Fixed** — field errors listed under form alert |

## Technical gaps

| ID | Claim | Status | Sev | Fix | Evidence |
|----|-------|--------|-----|-----|----------|
| T1–T52 | (prior revisions) | Mostly **Fixed** | — | — | See revision 4 |
| T53 | Coverage gate `fail_under=95` | **Done** | P1 | code | 95.01% Docker 2026-07-07; **reconfirm PASS 96%** 2026-07-27 (`verify_coverage.ps1`) |
| T54 | README project layout | **Fixed** | P2 | doc | MASTER §6.7 — layout refreshed |
| T55 | Export codec default | **Fixed** | P2 | code | `ExportConfig.codec` default `libx264` matches `config.yaml` / README (`core/config.py:135`) |
| T56 | GPU queue isolation | **Fixed** | P2 | code | `worker` queues now `${STREAMCLIP_WORKER_QUEUES:-default,gpu}`; set `default` with `--profile gpu` for isolation |
| T57 | Reframe `auto` preset | **Fixed** | P2 | doc | README preset table says "clip emotion heuristics"; matches `core/reframe.py` |
| T58 | Phase 2–4 backend features | **Fixed** | — | — | Profanity, words endpoint, waveform, `caption_words_per_group`, audio slate — verified in pipeline + API |
| T59 | License/commerce chain | **Fixed** | — | — | Lemon Squeezy webhook, email task, activation audit, admin revoke, perpetual JWT |
| T60 | `gpu-worker` volume parity | **Fixed** | P2 | both | `gpu-worker` mounts `./config:/app/config:ro` (`docker-compose.yml`) |
| T61 | CI coverage job | **Fixed** | P2 | code | `.github/workflows/test.yml` — MASTER §3.11 |

## UX gaps

| ID | Journey / control | Status | Sev | Fix | Evidence |
|----|-------------------|--------|-----|-----|----------|
| U1–U16 | (prior revisions) | Mostly **Fixed** | — | — | See revision 4 |
| U17 | Audio upload without feature gate | **Fixed** | P1 | code | `/api/meta` exposes `features.audio_ingest`; create form + `DirectUpload` restrict audio MIME when off |
| U18 | `ClipEditor` safe zones compile error | **Fixed** | P0 | code | `showSafeZones` state; `npm run typecheck` green |
| U19 | Words-per-group editor control | **Fixed** | P1 | code | Slider in Style section; saves `caption_words_per_group` |
| U20 | API docs in shipped app | **Removed** | P1 | code | OpenAPI/Swagger not in external UI; partners request privately; Docker dev may use `:8000/docs` with `STREAMCLIP_EXPOSE_API_DOCS=1` |
| U21 | `JobCard` nested `<button>` in `<Link>` | **Fixed** | P1 | code | Card uses `role="link"` + router; title edit stops propagation |
| U22 | Duplicate "Account" in header | **Fixed** | P2 | code | Settings vs Profile/Sign in labels in `header-nav.tsx` |
| U23 | SSE reconnect / `Last-Event-Id` | **Fixed** | P1 | code | `use-job-progress.ts` keeps EventSource on transient errors; polling after 20s fallback |
| U24 | SSE disconnect not surfaced | **Fixed** | P2 | code | `LiveProgress` amber banner for `reconnecting` / `polling` |
| U25 | `CreateJobRequest` fields not in form | **Fixed** | P2 | code | MASTER §2.15 — asset pack + profanity mode in create form |
| U26 | Save template omits profanity | **Fixed** | P2 | code | Template save/apply includes `profanity_filter` in `create-job-form.tsx` |
| U27 | Live browser upload → GPU pipeline → playable clip e2e | Partial | P2 | defer | Mock journey + API smoke green (rev 16 / T83); full upload→clips UI still deferred |
| U28 | Phase 3 UX (bug report, privacy, checklist) | **Fixed** | — | — | Wired in layout + settings hub |
| U78 | Create → home (not live overview) | **Fixed** | P1 | code | beta.24 — trailing slash + sync nav + jobs-miss ≠ home |
| U79 | Clip count drop when More options collapsed | **Fixed** | P1 | code | beta.24 — hidden `target_clips` always submitted |

## Modularity & duplication register

| Area | Finding | Severity | Recommendation |
|------|---------|----------|----------------|
| Publish routing | Job-scoped vs hub publish endpoints both delegate to `DistributionService` | P2 | Keep batch on jobs router; single-clip deprecated (MASTER §7.6) |
| Coverage vs velocity | Prior notify/ingest modules under-tested | **Fixed** | Batches 5–6 + ratchet; see MASTER §3.10 |

## Creator-platform gaps (mastery trajectory)

| ID | Capability | Status | Priority |
|----|------------|--------|----------|
| C1–C9 | (prior) | **Shipped** | — |
| C10 | Timeline editor (waveform + trim + safe zones) | **Shipped** | — | `trim-timeline.tsx`, `safe-zone-overlay.tsx`, waveform API |
| C11 | Transcript word editor | **Shipped** | — | `transcript-edit-panel.tsx`, GET words |
| C12 | Profanity filter (job + captions) | **Shipped** | — | `core/profanity.py`, create-job checkbox |
| C13 | Audio-to-clip (v2 SKU) | **Shipped** | — | `audio_slate.py`, `features.audio_ingest` gate |

## 110% coverage gate (beta blocker)

**Authoritative definition:** [`docs/MASTER_TODO.md`](MASTER_TODO.md) **§3.10**.

| Milestone | Target | Current (2026-07-27) |
|-----------|--------|----------------------|
| Line coverage | `fail_under = 95` (Phase 0) / 100 (Phase 1+) | **96%** — gate GREEN (reconfirm 2026-07-27; was 95.01% 2026-07-07) |
| Hot-path branches | ≥85% on pipeline_tasks, sse, distribution, job_service | Not measured (`branch = True` commented in `.coveragerc`) |
| Playwright e2e | ui-journey + `E2E_RUN=1` happy-path | **Green** host+CI (rev 16); live upload→clips UI still deferred (U27) |
| Web build | `npx next build` | **Green** |

See `docs/BETA_GO_LIVE.md`, `docs/BETA_TESTER_PLAN.md` §1.

## Resolved since last run (rev 16)

- T80 — Matrix green honesty (`pipeline_green` vs target-clips; 135 short on smoke fixture documented)
- T81 — Full e2e wired into `verify_stack -RunE2E` + CI ui-journey
- T82 — CONTRIBUTING + release-gate optional recheck pointers
- T84 — Gap ID collision (rev 16 T70–T72 → T80–T83; legacy a11y T70–T72 unchanged)

## Resolved since rev 15

- U78 — Create→home: fixed in tree (ship beta.24); known-issues still warn beta.23 testers
- U79 — Collapsed More options dropped `target_clips` from FormData (always hidden field now)
- D14 — Henna CTA **Generate clips** (was Submit); promote henna for public copy

## Resolved since revision 6 (2026-07-07)

- O8 — Weak AUTH secret warning (`core.config.is_weak_auth_secret`; startup `SECURITY_WARNING` outside development; covers `.env.example` placeholders + length < 32)
- T54 — README layout (MASTER §6.7)
- U25 — Create-job asset pack + profanity mode (MASTER §2.15)
- Distribution test debt — `tests/test_distribution_service.py`, `tests/test_distribution_vault_http.py`, OAuth helpers
- Coverage truth — MASTER §3.10, `scripts/verify_coverage.ps1`, `verify_stack.ps1 -WithCoverage`, CI `test.yml`

## Intentional deferrals (roadmap)

Tracked in **MASTER §2c** and §3:

- Speaker diarization (§2.18)
- Instagram Reels adapter (§2.22)
- TikTok direct publish (§2.1 remaining)
- Live browser upload → full GPU pipeline → playable clip e2e (U27 / T83; mock+API smoke shipped)
- yt-dlp subtitle reuse (§2.19)
- Hot-path branch coverage + ratchet to 100% line (§3.5–§3.7)

## Verification commands

```powershell
# Authoritative coverage (MASTER §3.10)
.\scripts\verify_coverage.ps1

# Fast stack + tests (no cov)
.\scripts\verify_stack.ps1

# Full Playwright e2e (ui-journey + happy-path)
.\scripts\verify_stack.ps1 -RunE2E
.\scripts\run_e2e_full.ps1 -ApiBase http://127.0.0.1:8765

# Create-option pipeline timing matrix (pipeline_green ≠ target_clips_green)
python scripts/matrix_create_pipeline_timing.py --summarize-only

# Pre-invite gate
.\scripts\verify_stack.ps1 -WithCoverage
```

```bash
cd web && npm run typecheck && npx next build
docker compose exec -T api python -c "from backend.main import app"
```

## How to re-run

Invoke skill: **`streamclip-gap-analysis`** (`.cursor/skills/streamclip-gap-analysis/SKILL.md`)

See also: `docs/PERFORMANCE.md`, `docs/TECHNICAL_DESIGN.md`, `docs/BETA_GO_LIVE.md`, `docs/MASTER_TODO.md`

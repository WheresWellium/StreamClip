# StreamClip Gap Analysis

**Last run:** 2026-07-28 (revision 10 — full dual-track audit: 23-claim technical matrix + 30-row UX sweep)

### Audit snapshot (2026-07-28 — Phase 0 exit strategic)

Strategic gap audit (desktop tester path + exit gates): **`tmp/gap-analysis-audit-2026-07-28.md`**.  
**Shipped (2026-07-28):** W2/W3/W4/G4 + **v1.0.0-beta.6** installer + cohort re-email 8/8.  
**Readiness ~90% shipped / ~70% Phase 0 exit.** Remaining: O4 cohort evidence, O5 on-call names, O11 EV signing. O14 Mac `.dmg` **published** (unsigned arm64 on beta.6).

## Executive summary

The **clip pipeline, distribution plane, and Phase 2–4 features are wired end-to-end**. Phase 0 **engineering invite gates are green** (coverage ≥95%, clean-slate stack). Remaining work is mostly **ops truth, cohort exit evidence, desktop trust (EV signing), and license/notify leftovers**. Coverage snapshot in SESSION_STATE ≈**96%**; Phase 1 still needs the **110%** row (MASTER §3.10 / §8.1).

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
| O11 | Windows EV signing / SmartScreen | P1 | ops | Tooling ✅ [`DESKTOP_SIGNING.md`](DESKTOP_SIGNING.md) Paths A–D — ☐ buy/install cert (MASTER §4.10); **beta.6 remains unsigned** |
| O12 | Loader / desktop publish | P1 | ops | **Closed 2026-07-28** — `v1.0.0-beta.6` published; UI journey e2e green (`test:e2e:ui-journey`) |
| O13 | Deprecated job publish route; N8N env alias | P2 | code | Defer |
| O14 | macOS DMG + notarization | P2 | ops | arm64 DMG on beta.6 ✅; **universal** pipeline ✅ (`arch: universal` + dual sidecars) — ☐ host rebuild/upload `qClip-mac-universal.dmg`; ☐ notarization |
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
| U27 | Playwright full journey | Partial | P2 | defer | MASTER §3.3 — blocks 110% gate |
| U28 | Phase 3 UX (bug report, privacy, checklist) | **Fixed** | — | — | Wired in layout + settings hub |

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
| Playwright smoke | `E2E_RUN=1` happy path | Scaffold exists; optional in Phase 0 |
| Web build | `npx next build` | **Green** |

See `docs/BETA_GO_LIVE.md`, `docs/BETA_TESTER_PLAN.md` §1.

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
- Full Playwright upload → clips e2e (§3.3)
- yt-dlp subtitle reuse (§2.19)
- Hot-path branch coverage + ratchet to 100% line (§3.5–§3.7)

## Verification commands

```powershell
# Authoritative coverage (MASTER §3.10)
.\scripts\verify_coverage.ps1

# Fast stack + tests (no cov)
.\scripts\verify_stack.ps1

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

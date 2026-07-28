# StreamClip — Feature Value Inventory

**Audience:** Board / executive · **Date:** 2026-07-28  
**Scope:** Shipped vs planned capabilities in `D:\Projects\streamclip` as of Phase 0 beta (engineering gates green; cohort exit in flight)

---

## Executive summary

StreamClip is a **GPU-bound, self-hosted clip pipeline** with an optional **Windows desktop bundle**, **Lemon Squeezy one-time licensing**, and a **Pro-gated distribution hub**. Community Edition (Apache 2.0) covers the core pipeline; commercial license unlocks desktop installer, distribution adapters, and priority support (`COMMERCIAL.md`).

**Buyers get:** local/self-hosted processing (no per-minute cloud metering), perpetual entitlement (default), and ownership of source media on their hardware. **Gaps vs SaaS clip competitors:** TikTok direct publish (inbox-only today), Instagram Reels, signed desktop installer, macOS GA, hosted multi-tenant cloud.

---

## 1. Core AI pipeline

| Feature | Buyer value | Tier | Status | Evidence |
|---------|-------------|------|--------|----------|
| URL + file ingest (yt-dlp, tier-aware quality) | Turn any VOD/podcast URL or upload into a job without re-uploading through a SaaS | Free (limits apply) | **Shipped** | `core/ingest/`, `backend/api/uploads.py`, `backend/api/jobs.py` |
| Tier-aware ingest routing (short/medium/long) | Lower cost on Shorts; skip expensive CV on short content | Free | **Shipped** | `core/ingest/classifier.py`, `core/config.py` (`IngestConfig`) |
| Full-source Whisper transcribe (GPU/CPU) | One pass per job — throughput win vs per-clip re-transcribe | Free | **Shipped** | `core/transcribe.py`, `docs/PERFORMANCE.md` |
| Highlight discovery (audio, spectral, optical flow, chat spikes) | Finds candidate moments without manual scrubbing | Free | **Shipped** | `core/highlights.py`, `core/peak_detection.py`, `core/chat_spikes.py` |
| LLM virality scoring (parallel, profile-aware) | Ranks clips for retention; degrades gracefully if LLM unreachable | Free | **Shipped** | `core/virality.py`, `core/content_profiles.py` |
| 9 content profiles (gaming, esports, podcast, IRL, etc.) | Vertical-tuned defaults without manual weight tuning | Free | **Shipped** | `core/content_profiles.py`, `core/creator_options.py` |
| Style learning from clip feedback | Channel learns which signals predict “good” clips over time | Free | **Shipped** | `core/style_learning.py` |
| YOLO + ByteTrack reframe (9:16, 1:1, 4:5, 16:9, 2:3) | Auto vertical/ square crop with subject tracking | Free | **Shipped** | `core/reframe.py` |
| Gaming reframe presets (FPS, MOBA, BR, IRL, podcast, sports) | HUD-safe crops for stream content | Free | **Shipped** | `core/reframe.py` (`PRESETS`) |
| 7 burned-in caption styles + “none” (8 catalogued) | Platform-native caption look without Submagic subscription | Free | **Shipped** | `core/captions.py`, `core/creator_options.py` (`CAPTION_STYLE_OPTIONS`) |
| Word-level karaoke / profanity filter | Compliance + readability for family-friendly channels | Free | **Shipped** | `core/captions.py`, `core/profanity.py` |
| NVENC / VideoToolbox export paths | GPU encode — primary throughput differentiator | Free (HW-dependent) | **Shipped** | `core/export_video.py`, `core/config.py` (`ExportConfig`) |
| Clip render idempotency + fan-out | Re-run safe; parallel clip renders | Free | **Shipped** | `core/tasks/pipeline_tasks.py`, `docs/PERFORMANCE.md` |
| Audio-to-clip (podcast/VO slate) | Monetizable SKU for non-video sources | Add-on SKU | **Shipped** (gated) | `core/config.py` (`FeaturesConfig.audio_ingest`), `core/commerce/entitlements.py` |
| LLM title suggestions (3 ranked hooks) | Faster publish copy; LLM cost borne by buyer’s key | Free today | **Shipped** | `core/title_suggestions.py`, `backend/api/title_suggestions.py` |
| Splice / crossfade merge | Multi-clip compilations for batch publish | Free | **Shipped** | `core/splice.py`, `backend/api/jobs.py` |
| Asset overlays (GIF/PNG) + semantic matching | Brand stickers at peak moments | Free (asset limits) | **Shipped** | `core/overlay.py`, `backend/api/assets.py` |
| Speaker diarization | Multi-speaker podcast clips | — | **Planned** | `docs/GAP_ANALYSIS.md` (MASTER §2.18) |
| yt-dlp subtitle reuse | Skip partial Whisper on long VOD | — | **Research** | `docs/PERFORMANCE.md` roadmap |

**Performance SLIs (buyer-visible):** 1h VOD → 5 clips target **<15 min GPU / <60 min CPU** (`docs/PERFORMANCE.md`); beta tolerance +25% (`docs/BETA_KNOWN_ISSUES.md`).

---

## 2. Distribution & publishing

| Feature | Buyer value | Tier | Status | Evidence |
|---------|-------------|------|--------|----------|
| Distribution hub (OAuth, queue, schedule) | One workspace to publish approved clips | **Pro** (install license or user tier) | **Shipped** | `backend/api/distribution.py`, `backend/middleware/distribution.py`, `core/distribution/service.py` |
| YouTube Shorts OAuth + upload | Direct publish without manual upload | **Pro** | **Shipped** | `core/distribution/youtube.py`, `docs/distribution-runbook.md` |
| TikTok adapter | TikTok workflow | **Pro** | **Partial** — inbox upload only until `video.publish` audit | `core/distribution/tiktok.py`, `TIKTOK_PUBLISH_ENABLED=false` default |
| Instagram Reels | Reels publish | **Pro** | **Planned** | `COMMERCIAL.md`, `docs/GAP_ANALYSIS.md` §2.22 |
| Batch publish from job | Approve many clips → queue at once | **Pro** | **Shipped** | `web/components/clips/job-clips-toolbar.tsx`, `backend/api/jobs.py` |
| Scheduled publish (Celery Beat / in-process beat) | Set-and-forget posting calendar | **Pro** | **Shipped** (desktop: app must run) | `core/celery_app.py`, `core/tasks/publish_tasks.py`, `docs/BETA_KNOWN_ISSUES.md` |
| Clip Vault (durable storage + quota) | Re-publish library without re-rendering | Free (quota) / **Pro** (higher) | **Shipped** | `backend/api/vault.py`, `core/billing.py` |
| Publish progress SSE + webhooks | Integrate with Zapier/Discord ops stacks | **Pro** | **Shipped** | `core/distribution/notify.py`, `core/webhooks.py` |
| BYO OAuth apps (self-host) | No StreamClip-managed OAuth dependency | **Pro** | **Shipped** | `core/distribution/credentials.py`, `docs/distribution-runbook.md` |
| Managed OAuth (cloud mode flag) | Lower friction for future hosted SKU | — | **Planned** (config stub) | `core/config.py` (`DistributionConfig.mode`) |

---

## 3. Web UX & creator workflow

| Feature | Buyer value | Tier | Status | Evidence |
|---------|-------------|------|--------|----------|
| Job create (URL, upload, profiles, profanity, asset pack) | Single form encodes pipeline knobs | Free | **Shipped** | `web/components/jobs/create-job-form.tsx`, `backend/api/jobs.py` |
| Live job progress (SSE + reconnect) | Trust during long GPU jobs | Free | **Shipped** | `web/components/jobs/` (SSE hooks), `core/progress_bus.py` |
| Clip editor (trim timeline, waveform, safe zones) | Fix boundaries without re-running discovery | Free | **Shipped** | `web/components/clips/clip-editor.tsx`, `web/components/clips/trim-timeline.tsx` |
| Transcript word editor | Fix bad ASR before burn-in | Free | **Shipped** | `web/components/clips/transcript-edit-panel.tsx` |
| Approve / reject workflow | Human gate before publish | Free | **Shipped** | Job/clip APIs, distribution gates |
| Templates (save/apply job settings) | Repeatable brand/pipeline presets | Free (limits) | **Shipped** | `backend/api/templates.py`, `web/components/jobs/` |
| Settings hub (license, distribution, vault, assets) | Operator control plane | Free / **Pro** | **Shipped** | `web/app/settings/page.tsx`, `web/components/settings/` |
| License panel + 3-seat management | Self-serve activation and seat release | **Pro** | **Shipped** | `web/components/settings/license-panel.tsx`, `backend/api/license.py` |
| Onboarding wizard | First-job path for new installs | Free | **Shipped** | `web/components/onboarding/onboarding-wizard.tsx` |
| Bug report / beta feedback | In-app support loop | Free | **Shipped** | `web/components/support/bug-report-dialog.tsx`, `backend/api/support.py` |
| Loading / brand screens | Desktop-quality first paint | Free | **Shipped** | `web/components/loading/` |
| Full Playwright upload→clips E2E | Regression safety | — | **Partial** (scaffold) | `docs/GAP_ANALYSIS.md` U27 |

---

## 4. Desktop (commercial)

| Feature | Buyer value | Tier | Status | Evidence |
|---------|-------------|------|--------|----------|
| Embedded runtime (no Docker) | Non-technical creators run locally | **Pro** (commercial) | **Shipped** (unsigned beta) | `docs/ADR-001-desktop-packaging.md`, `core/inprocess_worker.py` |
| SQLite + local storage profile | Single-folder install | **Pro** | **Shipped** | ADR-001, `core/config.py` |
| Bundled ffmpeg | No PATH dependency | **Pro** | **Shipped** | `core/ffmpeg_bins.py` |
| First-run model download | Smaller installer; progressive fetch | **Pro** | **Shipped** | `core/model_prefetch.py`, `docs/BETA_KNOWN_ISSUES.md` |
| Windows `.exe` installer | One-click install | **Pro** | **Shipped unsigned** | `scripts/build_desktop_installer.ps1`, `packaging/installer/` |
| EV code signing / SmartScreen | Enterprise trust | **Pro** | **Planned** | `docs/DESKTOP_SIGNING.md`, `docs/GAP_ANALYSIS.md` O11 |
| macOS DMG + notarization | Mac creator segment | **Pro** | **Scaffold only** | `docs/MACOS_INSTALLER.md`, `docs/GAP_ANALYSIS.md` O14 |
| Auto-update | Seamless patches | **Pro** | **Stub** | `docs/BETA_KNOWN_ISSUES.md`, MASTER §4.10 |

---

## 5. Self-host, ops & observability

| Feature | Buyer value | Tier | Status | Evidence |
|---------|-------------|------|--------|----------|
| Docker Compose production bundle | Reproducible server deploy | CE + **Pro** license | **Shipped** | `docker-compose.yml`, `docker-compose.prod.yml`, `deploy/PRODUCTION.md` |
| GPU worker profile (isolated queue) | Protects throughput from LLM/IO | Free | **Shipped** | `docker-compose.yml`, `docs/PERFORMANCE.md` |
| Prometheus metrics + stage histograms | Ops visibility / SLO tracking | Free | **Shipped** | `backend/api/metrics.py`, `core/pipeline_metrics.py` |
| Stack health endpoint | Automated invite gates | Free | **Shipped** | `backend/api/health.py`, `scripts/verify_stack.ps1` |
| Ops webhook (bug reports, job_failed, stack_degraded) | Operator alerting without SaaS | Free (config) | **Shipped** | `docs/OPS_ALERTING.md`, `core/notify/` |
| Job retention + cleanup | Disk hygiene on long-running hosts | Free | **Shipped** | `core/config.py` (`JobRetentionConfig`) |
| GHCR image publish path | Pinning for Phase 1 cohort | — | **Partial** | `docs/BETA_TESTER_PLAN.md` P1-4 |
| Hosted multi-tenant cloud | Zero-ops for non-Docker creators | — | **Removed / deferred** | `docs/BETA_KNOWN_ISSUES.md`, PLAN.md |

---

## 6. Licensing, commerce & security

| Feature | Buyer value | Tier | Status | Evidence |
|---------|-------------|------|--------|----------|
| Lemon Squeezy one-time checkout | Buy-once alignment with Gigapixel-style positioning | **Pro** | **Shipped** | `COMMERCIAL.md`, `backend/api/commerce.py` |
| `SCPRO-XXXX` keys, 3 machine seats | Studio/home lab without subscription | **Pro** | **Shipped** | `core/licensing.py`, `core/config.py` (`LicensingConfig.max_activations=3`) |
| Perpetual JWT entitlement (100y horizon) | True one-time promise | **Pro** | **Shipped** | `core/licensing.py` (`PERPETUAL_DAYS`, `entitlement_days: 0`) |
| Offline grace (7 days) | Laptop travel without phone-home | **Pro** | **Shipped** | `core/config.py`, `docs/BETA_KNOWN_ISSUES.md` |
| Seat list / release UX | Self-serve deactivation | **Pro** | **Shipped** | `web/components/settings/license-panel.tsx`, migration `0012_license_activation_seats` |
| Admin revoke | Fraud / chargeback handling | Admin | **Shipped** (JWT blocklist TODO) | `backend/api/admin.py`, `docs/BETA_KNOWN_ISSUES.md` |
| Auth secret strength enforcement | Production safety | Free | **Shipped** | `core/config.py`, `tests/test_auth_secret_strength.py` |
| Token encryption for OAuth (Fernet) | BYO credentials at rest | **Pro** | **Shipped** | `docs/distribution-runbook.md` |

---

## 7. Tier gating summary

Limits from `core/billing.py` (`TIER_LIMITS`):

| Limit | Free | Pro | Admin |
|-------|------|-----|-------|
| Target clips / job | 5 | 20 | 20 |
| Jobs / month | 30 | 500 | 1M |
| Source minutes / month | 600 | 10,000 | 1M |
| Templates | 5 | 20 | 100 |
| Assets | 10 | 50 | 500 |
| Vault clips | 25 | 500 | 5,000 |
| Vault storage | 10 GB | 50 GB | 500 GB |

**Distribution** requires Pro install license or Pro/Admin user tier (`backend/middleware/distribution.py` → `DistributionProRequired`).

**Commercial components** (desktop + distribution adapters) require StreamClip Pro license per `COMMERCIAL.md` regardless of CE pipeline access.

> **Note:** Monthly minute/job caps are **soft product guardrails** on self-host — not cloud metering. High-volume buyers expect Pro tier or future enterprise policy.

---

## 8. Monetizable surface

### Pro gates today (recommended paid bundle)

| Capability | Rationale |
|------------|-----------|
| YouTube Shorts publish + scheduling | Directly replaces Opus/Vizard scheduler subscription value |
| Distribution hub + OAuth | Platform adapters are commercial-licensed (`COMMERCIAL.md`) |
| Desktop installer | Non-Docker TAM; commercial-licensed |
| Elevated quotas (jobs, vault, clips) | Power creators outgrow Free guardrails |
| Priority support SLA | Enterprise expectation on paid SKU |

### Plumbed add-on SKUs (Lemon Squeezy variants)

| SKU | Status | Implementation |
|-----|--------|----------------|
| **Audio ingest** | **Shipped** (variant IDs in env) | `core/commerce/entitlements.py` — `audio_ingest_variant_ids`, `order_id_tags_audio_ingest` |
| **Clip title LLM pack** (future) | API shipped; SKU not separated | `core/title_suggestions.py` — candidate for gated LLM quota or one-time unlock |

### Future gate candidates (not priced yet)

| Capability | Notes |
|------------|-------|
| TikTok direct publish (`video.publish`) | Engineering blocked on app audit, not pricing |
| Instagram Reels adapter | MASTER §2.22 |
| Team / agency seats (>3 activations) | Upsell path vs Klipr Agency |
| Major-version upgrade fee | See `PRICING_ASSESSMENT.md` |
| Managed OAuth / hosted relay | Conflicts with buy-once unless beta-only |

---

## 9. Honest maturity snapshot

| Area | Maturity |
|------|----------|
| GPU pipeline | **Production-ready** for self-host beta |
| YouTube Shorts publish | **Production-ready** (BYO OAuth) |
| Commerce / licensing | **Production-ready** (jti blocklist deferred) |
| Desktop Windows | **Beta** (unsigned, manual update) |
| TikTok / Reels | **Not GA** |
| macOS / signing | **Not GA** |
| Hosted cloud | **Explicitly out of scope** |

---

*Research scratch files: `tmp/competitor-*.md` · Competitive positioning: `docs/commercial/COMPETITIVE_ANALYSIS.md` · Pricing scenarios: `docs/commercial/PRICING_ASSESSMENT.md`*

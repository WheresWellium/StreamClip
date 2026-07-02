---
name: streamclip-social-distribution
description: >-
  Implements and debugs StreamClip social distribution — Publish now, Schedule,
  Save to Clip Vault, YouTube Shorts and TikTok OAuth, Celery publish plane,
  and queue UI. Use when working on clip destinations, vault, OAuth connections,
  publish/schedule APIs, batch publish, SSE progress, or Pro/approval gates.
---

# StreamClip Social Distribution

## North star

Every clip offers **three destinations**: **Publish now**, **Schedule**, **Save to Clip Vault** — then post to **YouTube Shorts** and **TikTok** from the job grid or `/vault`, without leaving StreamClip.

## Clip Vault ≠ asset vault

| Concept | API / storage | Purpose |
|---------|---------------|---------|
| **Clip Vault** | `/api/vault`, `vault/{user_id}/…` in MinIO | Durable clip copies; survive job retention |
| **Asset vault** | `/api/assets` | GIFs/stickers for meme overlays |

Never conflate these in code, copy, or API calls.

## Phase status (implementation)

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Schema, token crypto, Pro gate, approval, platform registry | Done |
| 1 | VaultService, `/vault` UI, Save to Vault, tier limits | Done |
| 2 | Hybrid OAuth (BYO + managed), Connections tab, settings wizard | Done |
| 3 | DistributionService, Celery publish, destinations drawer, SSE | Done |
| 4 | Schedule queue, Beat poller, batch publish, Distribution hub | Done |
| 5 | Retry/cancel, webhooks, metrics, runbook, tests | **Partial** — core shipped; TikTok real upload and polish remain |

Plan reference (read-only): `C:\Users\locat\.cursor\plans\social_publish_ux_bc08d497.plan.md`

## Architecture

```
ClipDestinationsDrawer / VaultDestinationsDrawer
  → web/app/actions/distribution.ts
  → distributionApi (web/lib/api/client.ts)
  → backend/api/distribution.py
  → core/distribution/service.py (gates + enqueue)
  → core/tasks/publish_tasks.py (Celery upload)
  → Redis pub/sub (publish progress SSE)
```

### Key paths

| Area | Path |
|------|------|
| Service | `core/distribution/service.py` |
| Celery tasks | `core/tasks/publish_tasks.py` |
| Platform adapters | `core/distribution/youtube.py`, `tiktok.py` |
| OAuth / tokens | `core/distribution/credentials.py`, `tokens.py`, `connections.py` |
| Webhooks + metrics | `core/distribution/notify.py` |
| API router | `backend/api/distribution.py` |
| Vault API | `backend/api/vault.py`, `core/vault/service.py` |
| Batch publish | `backend/api/jobs.py` (`/{job_id}/clips/batch-publish`) |
| Job clip drawer | `web/components/clips/clip-destinations-drawer.tsx` |
| Vault drawer | `web/components/vault/vault-destinations-drawer.tsx` |
| Distribution hub | `web/app/distribution/page.tsx` |
| Vault hub | `web/app/vault/` |
| Pro gate UI | `web/components/distribution/pro-gate-modal.tsx` |
| Publish SSE hook | `web/hooks/use-publish-progress.ts` |
| SSE BFF | `web/app/api/distribution/publish-jobs/[id]/progress/route.ts` |

Platforms v1: `youtube_shorts`, `tiktok` (stub upload when `TIKTOK_PUBLISH_ENABLED=false`).

## Gates

| Gate | Where | Rule |
|------|-------|------|
| Auth | `require_user_id` | Signed in |
| Pro publish | `require_distribution_access` (`backend/middleware/distribution.py`) | User PRO/ADMIN or install Pro license |
| Approval | `DistributionService._resolve_source` | `clip.approval_status == approved` (or source clip for vault) |
| Connection | `PlatformConnectionRepository` | Active OAuth per platform |
| Vault save | auth only | Quota via `TierLimits.max_vault_clips` (`core/billing.py`) |

## API surface

Prefix: `/api/distribution`. Full table: [reference.md](reference.md).

| Endpoint | Purpose |
|----------|---------|
| `POST /publish` | Publish now (202) |
| `POST /schedule` | Schedule future publish (202) |
| `GET /publish-jobs/{id}/progress` | SSE progress stream |
| `POST /publish-jobs/{id}/retry` | Retry failed job |
| `POST /publish-jobs/{id}/cancel` | Cancel scheduled/pending |
| `POST /jobs/{id}/clips/batch-publish` | Batch publish approved clips (Pro) |
| OAuth | `/oauth/{platform}/start`, `/callback` |
| Connections | `GET/DELETE /connections` |

Publish accepts **either** `clip_id` **or** `vault_clip_id` (XOR enforced in service).

## Environment

```bash
STREAMCLIP_DISTRIBUTION__TOKEN_ENCRYPTION_KEY=   # Fernet; required for OAuth (503 if missing)
STREAMCLIP_DISTRIBUTION__WEB_ORIGIN=http://localhost:3000
STREAMCLIP_DISTRIBUTION__YOUTUBE_PUBLISH_ENABLED=true
STREAMCLIP_DISTRIBUTION__TIKTOK_PUBLISH_ENABLED=false
STREAMCLIP_DISTRIBUTION__YOUTUBE_CLIENT_ID=      # managed mode
STREAMCLIP_DISTRIBUTION__YOUTUBE_CLIENT_SECRET=
```

Config model: `core/config.py` → `DistributionConfig`. Ops detail: [streamclip-distribution-ops](../streamclip-distribution-ops/SKILL.md).

## Workers required

```bash
celery -A core.celery_app worker -Q default -l info
celery -A core.celery_app beat -l info   # process_due_scheduled_jobs every 60s
```

Beat entry in `core/celery_app.py`. Redis channel prefix: `streamclip:publish:` (`publish_pubsub_channel_prefix`).

## User journeys (verify)

1. **Job done** → clip card **Destinations** → Publish / Schedule / Vault
2. **`/vault`** → saved clips → publish/schedule via vault drawer
3. **`/distribution`** → Connections + Queue tabs
4. **`/settings`** → BYO OAuth wizard, license
5. Job toolbar → **batch publish** approved clips (Pro)

## Feature checklist (new work)

- [ ] Service gates in `DistributionService`
- [ ] Repository methods in `backend/db/repositories.py`
- [ ] Schemas in `backend/api/schemas.py`
- [ ] Router in `backend/api/distribution.py` or `jobs.py`
- [ ] Celery task if async work
- [ ] `distributionApi` + server action + UI component
- [ ] Pro gate + approval UX messaging (`useToastSafe`, not sonner)

## Related

| Resource | When |
|----------|------|
| [streamclip-development](../streamclip-development/SKILL.md) | Repo conventions, verification |
| [streamclip-distribution-ops](../streamclip-distribution-ops/SKILL.md) | Runbook, troubleshooting |
| `docs/distribution-runbook.md` | Operator reference |
| `tests/test_celery_publish.py`, `tests/test_publish_notify.py` | Publish plane tests |

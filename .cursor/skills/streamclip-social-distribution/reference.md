# Social Distribution — API & storage reference

## Distribution API (`/api/distribution`)

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/platforms` | optional | Platform list + connected flag |
| GET | `/oauth-apps` | Pro | BYO app config list |
| PUT | `/oauth-apps/{platform}` | Pro | Save BYO client id/secret |
| GET | `/oauth/{platform}/start` | Pro | Returns `auth_url` |
| GET | `/oauth/{platform}/callback` | — | OAuth redirect handler |
| GET | `/connections` | user | Active platform connections |
| DELETE | `/connections/{id}` | Pro | Disconnect |
| GET | `/publish-jobs` | user | User's publish queue |
| GET | `/publish-jobs/{id}` | user | Single job |
| POST | `/publish` | Pro | Publish now → 202 |
| POST | `/schedule` | Pro | Schedule → 202 |
| GET | `/publish-jobs/{id}/progress` | user | SSE (`Last-Event-Id`) |
| POST | `/publish-jobs/{id}/retry` | Pro | Failed jobs only |
| POST | `/publish-jobs/{id}/cancel` | Pro | scheduled/pending only |

## Jobs API (publish helpers)

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/api/jobs/{job_id}/clips/{clip_id}/publish` | Pro | Single-clip publish shortcut |
| POST | `/api/jobs/{job_id}/clips/batch-publish` | Pro | Approved finished clips only |

## Vault API (`/api/vault`)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/clips` | List vault clips |
| GET | `/quota` | `{ used, limit }` |
| POST | `/clips` | Save clip to vault |
| DELETE | `/clips/{id}` | Remove vault clip + MinIO keys |

## Assets API (`/api/assets`) — overlay memes only

Not Clip Vault. Used by semantic overlay pipeline for GIF/sticker library.

## Publish job statuses

`scheduled` → (Beat) → `pending` → `publishing` → `published` | `failed` | `cancelled`

In-flight guard: `pending`, `scheduled`, `publishing` block duplicate enqueue (`IN_FLIGHT_STATUSES` in service).

## Storage keys

| Source | Key pattern |
|--------|-------------|
| Job clip | `jobs/{job_id}/clips/{clip_id}/…` |
| Vault clip | `vault/{user_id}/{vault_clip_id}/…` |

Vault prefix excluded from job retention cleanup.

## Webhook events (`core/distribution/notify.py`)

| Event | When |
|-------|------|
| `publish.scheduled` | Future `scheduled_at` |
| `publish.published` | Upload succeeded |
| `publish.failed` | Terminal failure |
| `publish.cancelled` | User cancelled |

## Distribution error codes (selected)

| Code | Meaning |
|------|---------|
| `distribution_not_configured` | `TOKEN_ENCRYPTION_KEY` missing (503) |
| `pro_required` | Pro gate |
| `clip_not_approved` | Approval gate |
| `no_connection` | Platform not connected |
| `duplicate_in_flight` | Same clip+platform already queued |
| `platform_not_enabled` | Feature flag off |

See `core/distribution/errors.py` for full set.

## Tier vault limits (`core/billing.py`)

| Tier | `max_vault_clips` |
|------|-------------------|
| Free | 25 |
| Pro | 500 |
| Admin/install | 5000 |

## Backend routers (context)

| Router | Prefix | Notes |
|--------|--------|-------|
| `distribution` | `/api/distribution` | OAuth, publish, queue |
| `vault` | `/api/vault` | Clip Vault CRUD |
| `assets` | `/api/assets` | Overlay asset vault (not Clip Vault) |
| `jobs` | `/api/jobs` | Clips, approval, batch publish |

Full router list: `backend/main.py`.

## Web UI map

| File | Role |
|------|------|
| `web/components/clips/clip-destinations-drawer.tsx` | Publish / Schedule / Vault |
| `web/components/vault/vault-destinations-drawer.tsx` | Vault publish/schedule |
| `web/app/distribution/page.tsx` | Connections + queue |
| `web/app/vault/page.tsx` | Clip Vault hub |
| `web/app/actions/distribution.ts` | Publish server actions |
| `web/components/clips/job-clips-toolbar.tsx` | Batch publish |

## Quick grep pack

```bash
rg "DistributionService|publish_to_platform" core/ backend/
rg "distributionApi|ClipDestinationsDrawer" web/
rg "require_distribution_access|ClipNotApproved" backend/ core/
```

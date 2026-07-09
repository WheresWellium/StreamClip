# StreamClip Cloud MVP — Multi-tenant Architecture

> **Status: design-stage only — nothing here is implemented.** The former `backend/cloud/tenant.py` stub and `docker-compose.cloud.yml` were **removed** (MASTER §2.10, 2026-07-09). No code reads `STREAMCLIP_CLOUD_MODE`. Stripe has been removed from the product (Lemon Squeezy is the billing provider). This doc is a future-architecture sketch only.

## Overview

The cloud deployment would extend the self-hosted stack with tenant isolation, row-level security (RLS), and usage metering. This document describes a target architecture only — no middleware stub ships in-tree.

## Tenancy model

| Layer | Strategy |
|-------|----------|
| Identity | Auth0 / Clerk JWT with `tenant_id` claim |
| API | `X-Tenant-Id` header → tenant context (not implemented) |
| Database | PostgreSQL schema-per-tenant or shared schema + RLS |
| Storage | S3 prefix `tenants/{tenant_id}/` |
| Queue | Celery task headers include `tenant_id` |

## Row-level security (RLS)

Enable RLS on tenant-scoped tables:

```sql
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY jobs_tenant_isolation ON jobs
  USING (tenant_id = current_setting('app.tenant_id')::text);
```

Set tenant per connection in middleware:

```python
await db.execute(text("SET app.tenant_id = :tid"), {"tid": ctx.tenant_id})
```

## Stripe metering

| Event | Stripe meter |
|-------|----------------|
| Job created | `streamclip.jobs` |
| Minutes processed | `streamclip.minutes` |
| Clips rendered | `streamclip.clips` |

Webhook handler upgrades `users.tier` on `checkout.session.completed` (see `core/billing.py` stub).

Env vars:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_METER_JOBS_ID`
- `STRIPE_METER_MINUTES_ID`

## Deployment

Use a dedicated compose overlay when implementing. Add:

1. Managed Postgres with RLS policies applied via Alembic
2. Redis Cluster for broker + SSE pub/sub
3. Horizontal API replicas behind a load balancer
4. GPU worker pool autoscaled on queue depth
5. Vercel or containerized Next.js for web

## Security

- Never share JWT signing keys across tenants
- Encrypt `platform_connections.access_token_enc` at rest
- Audit log all cross-tenant admin actions
- SOC2: separate prod/staging tenants, quarterly access reviews

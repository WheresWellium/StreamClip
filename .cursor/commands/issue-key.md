---
description: Issue a StreamClip beta license key (one-time or email-bound) and append to tmp/beta_key_activity.jsonl.
---

# /issue-key — StreamClip license key generator

Issue a Pro or max-access **admin** license key. Logs every issuance to `tmp/beta_key_activity.jsonl` (never commit).

Parse **`$ARGUMENTS`**:

| Input | Action |
|-------|--------|
| *(empty)* | One-time **admin** key (no email) |
| `user@example.com` | Email-bound **admin** key |
| `--tier pro` | Pro tier instead of admin |
| `--list` | Show recent activity log rows |
| `--dry-run` | Print + log only, no DB write |

Combine flags: `/issue-key --tier pro user@example.com`

## Preflight

1. **Docker stack up** — `docker compose ps` shows `api` running.
2. **Repo root** — commands run from StreamClip project root.
3. **Windows mount** — if the script is missing in the container, copy it first (see Commands).

Stop and report if `api` is not running.

## Plan

State what you will issue:

- **One-time** (no email in args): `otp-*` order id, `kind: one_time` in log.
- **Email-bound**: `customer_email` set, tester must register with that email.
- Default tier: **admin** (max access). Use `--tier pro` only when user asks.

## Commands

Preferred (PowerShell, handles container sync):

```powershell
.\scripts\issue_access_key.ps1
.\scripts\issue_access_key.ps1 -Email user@example.com
.\scripts\issue_access_key.ps1 -Tier admin -Email user@example.com
.\scripts\issue_access_key.ps1 -List -Limit 30
```

Direct (inside container):

```powershell
docker compose cp scripts/issue_access_key.py api:/app/scripts/issue_access_key.py
docker compose exec api sh -c "PYTHONPATH=/app python scripts/issue_access_key.py"
docker compose exec api sh -c "PYTHONPATH=/app python scripts/issue_access_key.py --email user@example.com"
docker compose exec api sh -c "PYTHONPATH=/app python scripts/issue_access_key.py --list --limit 20"
```

Map `$ARGUMENTS` to CLI flags before running.

## Verification

1. Command exits 0.
2. JSON output includes `license_key`, `order_id`, `tier`, `kind`.
3. New line appended to `tmp/beta_key_activity.jsonl` (unless `--list` only).

## Summary

Present to the user:

```
## Key issued
- **Kind**: one_time | email_bound
- **Tier**: admin | pro
- **Email**: (none) | user@example.com
- **License key**: SCPRO-…
- **Order ID**: otp-… | beta-…
- **Log**: tmp/beta_key_activity.jsonl
```

**One-time:** paste in **Settings → License** (no email match required).  
**Email-bound:** register/login with that email, then activate in Settings.

## Next steps

- `/issue-key --list` — audit recent issuances
- Send key via invite template in `docs/BETA_OPS_PHASE0.md` (if present)
- Local dev max access without a key: `grant_dev_pro.py` (upgrades DB users + auto-activates)

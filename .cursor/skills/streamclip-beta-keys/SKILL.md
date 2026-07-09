---
name: streamclip-beta-keys
description: Issues StreamClip beta license keys (one-time or email-bound) via Docker, logs to tmp/beta_key_activity.jsonl. Use when the user runs /issue-key, asks to generate a beta key, max-access key, admin key, or OTP license key.
disable-model-invocation: true
---

# StreamClip beta key issuance

## When to use

- User runs **`/issue-key`** or asks to generate a license / beta / admin key
- Phase 0 ops: invite testers, max-access testing, one-time keys

## Quick commands

```powershell
# One-time admin key (default max access)
.\scripts\issue_access_key.ps1

# Email-bound admin key
.\scripts\issue_access_key.ps1 -Email user@example.com

# Pro tier (distribution only, no admin API)
.\scripts\issue_access_key.ps1 -Tier pro -Email user@example.com

# Activity log
.\scripts\issue_access_key.ps1 -List -Limit 30
```

Docker fallback (always `PYTHONPATH=/app`; copy script if mount stale on Windows):

```powershell
docker compose cp scripts/issue_access_key.py api:/app/scripts/issue_access_key.py
docker compose exec api sh -c "PYTHONPATH=/app python scripts/issue_access_key.py [--email ADDR] [--tier pro|admin] [--list]"
```

## Behavior

| Mode | CLI | DB `customer_email` | Tester flow |
|------|-----|---------------------|-------------|
| **One-time** | no `--email` | `null` | Paste key in Settings → License |
| **Email-bound** | `--email` | set | Register with same email, then activate |

Default tier: **admin** (distribution + admin API + highest quotas).  
Pro tier: paid-equivalent entitlements only.

## Activity log

- Path: `tmp/beta_key_activity.jsonl`
- Format: one JSON object per line (`ts`, `key_id`, `kind`, `tier`, `email`, `license_key`, `order_id`, `status`)
- **Never commit** — contains plaintext keys
- List: `--list` or `.\scripts\issue_access_key.ps1 -List`

## Agent output template

After a successful run, show the user:

1. License key (`SCPRO-…`)
2. Kind (one-time vs email-bound)
3. Tier
4. Order ID
5. Log file path

## Local dev shortcut (no issued key)

Operator machine only — upgrades users to admin + auto-activates install license:

```powershell
docker compose exec api sh -c "PYTHONPATH=/app python scripts/grant_dev_pro.py"
```

## Related

- Slash command: `.cursor/commands/issue-key.md`
- Script: `scripts/issue_access_key.py`
- OAuth redirect URIs: `{WEB_ORIGIN}/api/distribution/oauth/{platform}/callback`

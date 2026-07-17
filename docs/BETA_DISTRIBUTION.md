# Beta distribution — operator runbook (Lemon Squeezy)

**Audience:** Operator only (not published on henna).  
**Companion:** [BETA_INVITE_PACK.md](BETA_INVITE_PACK.md), [BETA_OPS_PHASE0.md](BETA_OPS_PHASE0.md) §6

---

## Overview

| Layer | Host |
|-------|------|
| Docs | [streamclip-henna.vercel.app](https://streamclip-henna.vercel.app/) (Vercel) |
| Downloads + keys | Lemon Squeezy Lead Magnet ($0) |
| App runtime | Tester local Docker or `.exe` |

---

## Lemon Squeezy product setup

1. **New Product** → pricing type **Lead Magnet** ($0)
2. Name: `StreamClip Phase 0 Beta`
3. **Disable** storefront listing (unlisted checkout only)
4. **Enable** license keys — perpetual, activation limit **3**
5. Attach files:
   - `dist/streamclip-beta-kit-Source-*.zip` from `.\scripts\prepare_beta_kit.ps1`
   - `apps\desktop\release\StreamClip-Setup-win-x64.exe` from `.\scripts\publish_desktop_release.ps1`
6. Receipt button → `https://streamclip-henna.vercel.app/BETA_TESTER_QUICKSTART/`
7. Webhook → `{API_ORIGIN}/api/commerce/webhooks/lemon-squeezy`
8. Record variant ID → `STREAMCLIP_COMMERCE__LEMON_SQUEEZY_BETA_VARIANT_ID`

---

## Environment variables

```bash
STREAMCLIP_COMMERCE__LEMON_SQUEEZY_API_KEY=
STREAMCLIP_COMMERCE__LEMON_SQUEEZY_WEBHOOK_SECRET=
STREAMCLIP_COMMERCE__LEMON_SQUEEZY_BETA_VARIANT_ID=
STREAMCLIP_COMMERCE__LEMON_SQUEEZY_PRO_VARIANT_ID=      # paid SKU (later)
STREAMCLIP_COMMERCE__LEMON_SQUEEZY_CHECKOUT_URL=https://<store>.lemonsqueezy.com/checkout/buy/<variant_id>
```

Verify: `.\scripts\verify_ls_beta_config.ps1`

---

## Invite modes

### LemonSqueezy (new cohorts)

```powershell
$env:STREAMCLIP_COMMERCE__LEMON_SQUEEZY_CHECKOUT_URL = "https://..."
.\scripts\prepare_invite_pack.ps1 -Mode LemonSqueezy -CohortCsv cohort.csv
```

### Manual (existing cohort — inline SCPRO key)

```powershell
docker compose exec -e PYTHONPATH=/app -T api python scripts/issue_beta_keys.py --csv cohort.csv `
  > dist/phase0-invite-pack/keys.csv
.\scripts\prepare_invite_pack.ps1 -Mode Manual -KeysCsv dist\phase0-invite-pack\keys.csv
```

Testers with manual keys run once:

```bash
docker compose exec -e PYTHONPATH=/app api python scripts/import_invite_license.py \
  --key SCPRO-... --tier admin
```

---

## Definition of done (before invites)

- [ ] `.\scripts\verify_ls_beta_config.ps1` green
- [ ] LS test-mode $0 checkout → key + downloads in receipt
- [ ] Clean Windows VM: zip → `start_local.ps1` → LS key activates
- [ ] Clean Windows VM: manual key → `import_invite_license.py` → activate
- [ ] Henna `BETA_DOWNLOAD` has no GitHub-only links
- [ ] `pytest tests/test_license_chain.py tests/test_lemon_squeezy_client.py` green

---

## Rollback

| Incident | Action |
|----------|--------|
| Bad build uploaded | Replace files on LS product; email cohort |
| Checkout URL leaked | Disable product; create new variant; new checkout URL |
| LS outage | Manual mode invites + `issue_beta_keys.py` + zip via Drive |
| Activation fails | Check API key on api container; LS dashboard key status |

---

## Migration off Lemon Squeezy (future)

1. Export keys from LS dashboard
2. Batch `import_invite_license.py` or paid provider License API
3. Retire LS checkout links in docs; point to new commerce URL

`issue_beta_keys.py` remains the operator fallback permanently.

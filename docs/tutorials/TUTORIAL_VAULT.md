# Tutorial — Clip Vault

!!! warning "Not on the public docs site"
    Creators: finish a job via **[First clip](../BETA_TESTER_QUICKSTART.md)**, then use **Vault** in the app. This page is an operator deep-dive kept in the repo only.

**Time:** ~5 minutes · **Prerequisite:** At least one **approved** or **done** clip from [First clip](../BETA_TESTER_QUICKSTART.md)

The **Vault** is durable storage for clips you want to keep across jobs — publish later, reuse overlays, or organize a content library. Beta tier limits apply.

---

## What the Vault stores

| Stored | Not stored |
|--------|------------|
| Rendered MP4 (MinIO `vault/` prefix) | Raw full VOD |
| Title, metadata, publish history | Unapproved draft renders |
| Link back to source job | Ephemeral job-only previews |

Vault clips survive `docker compose down` — data lives in Docker volumes.

---

## Step 1 — Save a clip to Vault

**From a job clip card:**

1. Open a finished clip on the job page
2. Click **Save to Vault** (or **Vault** icon on the clip card)
3. Toast confirms the clip was saved

**From the clip editor:**

1. Open the editor on an approved clip
2. Use **Save to Vault** in the actions menu

!!! tip
    You can save before or after approve. Approved clips are easier to publish directly from Vault later.

---

## Step 2 — Open the Vault

1. Sidebar → **Vault**
2. Grid shows thumbnails, titles, and save dates
3. Click a clip to preview or open **Destinations** (publish to connected platforms)

---

## Step 3 — Rename a clip

1. In the Vault grid, click the **pencil** icon on a clip row
2. Edit the title inline
3. Press **Enter** or click **Save**

Renames call `PATCH /api/vault/clips/{id}` — instant, no re-render.

---

## Step 4 — Check your quota

Vault capacity is tier-limited:

1. **Vault** page header shows **used / limit** (e.g. `3 / 50`)
2. Or open browser devtools → `GET /api/vault/quota`

| Tier (beta) | Typical limit |
|-------------|---------------|
| Free / unlicensed | Lower cap |
| Beta / admin key | Full quota unlocked |

!!! info "Beta keys"
    Keys from your invite email unlock **admin-tier** limits. Activate in **Settings → License** — optional but recommended for T0-5. See [Install](../BETA_DOWNLOAD.md).

When quota is full, saving returns an error — delete old vault clips or upgrade tier.

---

## Step 5 — Publish from Vault

1. Open a vault clip → **Destinations**
2. Select **YouTube Shorts** (must be connected — [Publish tutorial](TUTORIAL_PUBLISH_YOUTUBE.md))
3. Publish now or schedule

Vault clips retain their own publish history in the Destinations drawer.

---

## Step 6 — Remove a clip

1. Vault grid → **Remove** (trash icon)
2. Confirm deletion

This removes the vault record and storage object. It does **not** delete the original job clip.

---

## Step 7 — Verify storage (optional)

=== "Windows"

    ```powershell
    docker compose logs worker --tail 20
    ```

=== "macOS"

    ```bash
    docker compose logs worker --tail 20
    ```

---

## Acceptance (T0-5)

From [Beta test plan](../BETA_TESTER_PLAN.md#43-required-tester-flows-acceptance):

- [ ] Clip saved to Vault from a job
- [ ] Renamed successfully in Vault grid
- [ ] Quota display matches expected tier

---

## Next steps

| Goal | Tutorial |
|------|----------|
| YouTube publish | [Publish YouTube](TUTORIAL_PUBLISH_YOUTUBE.md) |
| Performance tuning | [GPU setup](TUTORIAL_GPU_SETUP.md) |

---

*See also: [Beta quickstart](../BETA_TESTER_QUICKSTART.md) · [Known issues](../BETA_KNOWN_ISSUES.md)*

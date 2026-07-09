# Tutorial — Publish to YouTube Shorts

**Time:** ~10 minutes · **Prerequisite:** [Edit & approve](TUTORIAL_EDIT_APPROVE.md) — at least one **approved** clip

Connect your own Google account (**BYO OAuth**), configure distribution settings, and publish a vertical clip to **YouTube Shorts**.

---

## How OAuth works in beta

StreamClip uses **bring-your-own OAuth** for Phase 0:

- Tokens are encrypted locally (`TOKEN_ENCRYPTION_KEY` in `.env`)
- Local dev compose ships with a **DEV-ONLY** key + `WEB_ORIGIN=http://localhost:3000` — OAuth works out of the box on localhost
- Production/ hosted installs need their own Google Cloud OAuth app — see [Distribution runbook](../distribution-runbook.md)

!!! warning "Do not reuse dev encryption keys in production"
    Generate a fresh Fernet key per deployment.

---

## Step 1 — Create a Google Cloud OAuth app (BYO)

Skip this if you're testing on localhost with the bundled dev config.

1. Open [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
2. Create **OAuth 2.0 Client ID** (type: **Web application**)
3. Add authorized redirect URI:

   ```
   http://localhost:3000/api/distribution/oauth/youtube/callback
   ```

   For hosted installs, replace `localhost:3000` with your `WEB_ORIGIN`.

4. Enable **YouTube Data API v3** for the project
5. Copy **Client ID** and **Client secret** into `.env`:

   ```bash
   STREAMCLIP_DISTRIBUTION__YOUTUBE_CLIENT_ID=...
   STREAMCLIP_DISTRIBUTION__YOUTUBE_CLIENT_SECRET=...
   STREAMCLIP_DISTRIBUTION__YOUTUBE_PUBLISH_ENABLED=true
   ```

6. Restart the stack:

   === "Windows"
       ```powershell
       docker compose up -d
       ```
   === "macOS"
       ```bash
       docker compose up -d
       ```

---

## Step 2 — Connect YouTube in Settings

1. Open [http://localhost:3000](http://localhost:3000) → **Settings**
2. Go to **Distribution**
3. Under **YouTube Shorts**, click **Connect**
4. Sign in with the Google account that owns your channel
5. Grant the requested YouTube scopes
6. Return to StreamClip — connection status should show **Connected**

!!! tip "Multiple channels"
    Beta supports one connection per platform per user. Reconnect to switch accounts.

---

## Step 3 — Distribution settings

Review these before your first publish:

| Setting | Location | Notes |
|---------|----------|-------|
| Default visibility | Distribution → YouTube | Public / Unlisted / Private |
| Title template | Per publish or queue edit | Uses clip title by default |
| Scheduled publish | Distribution → Queue | Requires Celery **Beat** running in Docker stack |
| Webhook URL | Settings → Webhooks (optional) | Fires on publish complete |

Scheduled posts need the `beat` service healthy — check `docker compose ps`.

---

## Step 4 — Publish one clip

1. Open an **approved** clip (see [Edit & approve](TUTORIAL_EDIT_APPROVE.md))
2. Click **Publish** or open **Destinations**
3. Select **YouTube Shorts**
4. Confirm title and visibility
5. Click **Publish now**

Live upload progress streams via SSE on the **Distribution → Queue** tab.

---

## Step 5 — Confirm success

| Outcome | What you see |
|---------|--------------|
| Success | Queue row → **published**; YouTube Studio shows new Short |
| Error | Queue row → **failed** with message (quota, auth, format) |
| In progress | **publishing** with progress bar |

Check queue: **Distribution → Queue** in the sidebar.

---

## Step 6 — Batch publish (optional)

From a finished job with multiple approved clips:

1. Job toolbar → **Publish approved (N)**
2. Pick platform → confirm

All approved clips enqueue as separate publish jobs.

---

## TikTok note

TikTok direct publish is **inbox-only** during beta. Clips land in TikTok drafts — finish in the TikTok app. See [Known issues](../BETA_KNOWN_ISSUES.md).

---

## Troubleshooting OAuth

| Symptom | Fix |
|---------|-----|
| Redirect URI mismatch | Match Google Console URI to `WEB_ORIGIN` exactly |
| Connect button loops | Clear cookies; restart `api` container |
| `invalid_grant` on publish | Reconnect YouTube in Settings |
| Upload fails format check | Clip must be vertical 9:16 — re-export from editor |

More: [Troubleshooting tutorial](TUTORIAL_TROUBLESHOOTING.md)

---

## Acceptance (T0-4)

- [ ] YouTube connection saved in Settings
- [ ] Publish reaches **published** or shows a clear, actionable error

---

*See also: [Beta quickstart](../BETA_TESTER_QUICKSTART.md) · [Distribution runbook](../distribution-runbook.md)*

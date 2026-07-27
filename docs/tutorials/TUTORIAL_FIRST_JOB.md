# Tutorial — Your First Job

**Time:** ~5 minutes to start + waiting while clips render · **Prerequisite:** [Install tutorial](TUTORIAL_INSTALL.md)

This walks you through turning **one video link** into short clips.

---

## Before you start

- qClip is running — you opened [http://localhost:3000](http://localhost:3000) and it loaded
- You have a **public** video link (anyone can watch it without logging in)

!!! tip "Using a Mac without a graphics card?"
    Start with a **short video** (10–20 minutes). Long videos take much longer on CPU-only machines.

---

## Step 1 — Create a job

1. On the home screen, click **New job**
2. Paste a link from this list:

| Where | Example link shape |
|-------|-------------------|
| Twitch VOD | `https://www.twitch.tv/videos/...` |
| YouTube | `https://www.youtube.com/watch?v=...` |
| Kick | `https://kick.com/...` |
| Direct file | A public `.mp4` link |

3. Optionally type a **title** (helps you find it later)
4. Click **Submit**

You should land on a **job page** with a progress bar.

---

## Step 2 — Watch progress

The page updates **by itself** — you do not need to refresh.

Stages you will see, in order:

```
download → transcribe → detect highlights → render clips
```

- **Download** — qClip saves the source video to your machine
- **Transcribe** — speech is turned into text
- **Detect highlights** — software picks exciting moments
- **Render clips** — short vertical videos are created

If the progress bar pauses for a few seconds, that is normal. If nothing changes for **30+ minutes**, see [Troubleshooting](TUTORIAL_TROUBLESHOOTING.md).

---

## Step 3 — Review clips as they appear

Finished clips show up in a grid on the same page:

- **Preview** — click to watch
- **Transcript** — click **Show transcript** to read what was said
- **Score** — may show `0` if the local AI helper is offline (known beta quirk; clips still work)

You can watch clips while others are still rendering.

---

## Step 4 — Job finished

When everything is done:

- Progress shows **100%**
- Status says **done**
- All clips are listed

---

## How long will it take?

| Your setup | About 1 hour of source video |
|------------|------------------------------|
| Windows + NVIDIA graphics card | ~20–25 minutes |
| Windows or Mac, CPU only | ~60–90+ minutes |

---

## What to do next

| Goal | Guide |
|------|-------|
| Edit title, trim, fix words | [Edit & approve](TUTORIAL_EDIT_APPROVE.md) |
| Save favorites | [Vault](TUTORIAL_VAULT.md) |
| Post to YouTube Shorts | [Publish YouTube](TUTORIAL_PUBLISH_YOUTUBE.md) |

---

## If something goes wrong

=== "Windows"

    ```powershell
    docker compose logs api worker --tail 50
    ```

=== "macOS"

    ```bash
    docker compose logs api worker --tail 50
    ```

Copy the **job ID** from the job page and open **Help menu (?)** → **Report a bug**.

---

*See also: [Beta quickstart](../BETA_TESTER_QUICKSTART.md) · [Known issues](../BETA_KNOWN_ISSUES.md)*

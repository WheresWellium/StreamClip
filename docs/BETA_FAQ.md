# qClip Beta — FAQ

Short answers for Phase 0 testers. For step-by-step setup, see [Get qClip](BETA_DOWNLOAD.md) and the [15-minute quickstart](BETA_TESTER_QUICKSTART.md).

---

## How do I install?

**[Download qClip-Setup-win-x64.exe](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe)** — run it, open qClip from the Start menu.

No Docker, no zip, no GitHub account.

---

## I'm on a Mac — how do I install?

The one-click `.dmg` is **not a public download yet**. Mac beta uses **Docker self-host**:

1. Install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/) (Apple Silicon or Intel).
2. Clone or download the repo (reply to your invite email if you need a link).
3. From the repo: `cp .env.example .env` then `docker compose up -d`.
4. Open [http://localhost:3000](http://localhost:3000), import your SCPRO key once (see [quickstart Docker step 5](BETA_TESTER_QUICKSTART.md#docker-step-5-activate-your-license-key)), then paste it in **Settings → License**.

Clips run **CPU-only** on Mac — slower than GPU Windows Docker; try shorter sources. Full steps: [Get qClip](BETA_DOWNLOAD.md#advanced-docker-self-host-operators) (macOS tab).

---

## Where is my license key?

In your **BETA TEST INFO** invite email. Copy the `SCPRO-…` key and paste it in **Settings → License**.

---

## "Link jobs" error?

Click **Skip**. This is a known desktop bug — a fix is coming. Your jobs still work on your PC; you can create and review clips without linking.

---

## Do I need to sign up?

No. An account is optional. You can paste a URL, upload a file, and clip on desktop without signing up or logging in.

---

## Why is first run slow?

qClip downloads AI speech models once on first use (~1–2 GB for the beta `medium` model). Keep the app open — a banner shows download progress. Later runs are much faster.

---

## SmartScreen warning?

This beta build is not code-signed yet, so Windows may show **"Windows protected your PC."** That does not mean the file is a virus.

1. Click **More info**
2. Click **Run anyway**
3. Finish install and open qClip

---

## Who do I contact?

In the app: **Help → Beta feedback** or **Report a bug**. You can also reply to your invite email if you need a human.

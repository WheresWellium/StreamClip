# qClip Beta — FAQ

Short answers. Step-by-step: [Get qClip](BETA_DOWNLOAD.md) · [Quickstart](BETA_TESTER_QUICKSTART.md).

---

## How do I install (Windows)?

**[Download qClip-Setup-win-x64.exe](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe)** (v1.0.0-beta.6) → run → open from Start menu → paste your key in **Settings → License**.

No Docker, no zip, no GitHub account.

---

## I'm on a Mac — how do I install?

No public `.dmg` yet. Use **Docker Desktop**:

1. Install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/).
2. Get the repo (reply to your invite if you need a link).
3. `cp .env.example .env` then `docker compose up -d`.
4. Open [http://localhost:3000](http://localhost:3000), import your key once ([quickstart Docker step 5](BETA_TESTER_QUICKSTART.md#docker-step-5-activate-your-license-key)), then **Settings → License**.

CPU-only on Mac — try shorter sources. Full steps: [Get qClip → Docker](BETA_DOWNLOAD.md#advanced-docker-self-host-operators).

---

## Where is my license key?

In your invite / setup email (`SCPRO-…`). Paste it in **Settings → License**.

Desktop **beta.6+** seeds cohort keys at boot — paste and activate. Docker self-host still needs a one-time `import_invite_license.py` (see quickstart).

---

## Upgraded from beta.5?

Re-download [Latest](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe) and **re-paste your license key once**. That refreshes install secrets and the claim-device fix.

---

## "Link jobs" error?

Update to **beta.6**. On an old beta.5 install, click **Skip** — jobs still work locally.

---

## Do I need to sign up?

No. Account optional. Clip from a URL or upload without signing in.

---

## Why is first run slow?

Speech models download once (~1.5 GB for `medium`). Keep the app open; the loading screen shows progress.

---

## SmartScreen warning?

Unsigned beta — not a virus. **More info → Run anyway**.

---

## Who do I contact?

**Help → Beta feedback** or **Report a bug**, or reply to your invite email.

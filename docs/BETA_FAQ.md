# FAQ (operator notes)

> **Creators:** use the public page — [Download & how to use](index.md) (henna home). This file is **not published**.

Short answers for operators. Creator-facing steps live on henna home.

---

## How do I install on Windows?

**Call to action:** [Download the installer](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe) → run → **Settings → License** → paste your `SCPRO-…` key.

Details: [Install qClip](BETA_DOWNLOAD.md#one-click-installers)

---

## How do I install on Mac?

**Call to action:** [Download qClip-mac-arm64.dmg](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-mac-arm64.dmg) (`1.0.0-beta.26`) → Applications → right-click **Open** (unsigned) → **Settings → License**. Same code train as Windows Latest.

Apple Silicon on Latest; universal (Intel + Silicon) via local Mac rebuild. Details: [Install → macOS](BETA_DOWNLOAD.md#macos). Docker remains an [operator fallback](BETA_DOWNLOAD.md#macos-docker-fallback).

---

## Where is my license key?

In your invite / setup email (`SCPRO-…`). Paste it in **Settings → License**.

- **Windows / Mac desktop (beta.6+):** paste and activate — keys are seeded at boot.  
- **Docker:** run `import_invite_license.py` once first — see [Install → Docker fallback](BETA_DOWNLOAD.md#macos-docker-fallback).

---

## I upgraded from an older beta

Install [Latest](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe) and **re-paste your key once**.

---

## "Link jobs" error?

Update to **beta.8**. On beta.5 only, click **Skip** — local jobs still work.

**Call to action:** [Download Latest](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe) (`1.0.0-beta.26`)

---

## Do I need to sign up?

No. Account optional. Clip from a URL or upload without signing in.

---

## Why is first run slow?

Models download once (~1.5 GB). Keep the app open — the loading screen shows progress. Then create a job: [First clip](BETA_TESTER_QUICKSTART.md).

---

## SmartScreen warning?

Unsigned beta — not a virus. **More info → Run anyway**.

---

## Who do I contact?

Use in-app **Help → Report a bug** / **Beta feedback** (files a GitHub Issue on our board), the [GitHub beta bug template](https://github.com/WheresWellium/StreamClip/issues/new?template=beta-bug.yml) as backup, or reply to your invite email.

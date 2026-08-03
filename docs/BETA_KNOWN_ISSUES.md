# Known issues (operator notes)

> **Creators:** use the public page — [Download & how to use](index.md) (henna home). This file is **not published**.

**Updated:** 2026-08-03 · Current Windows build: **v1.0.0-beta.21**

---

## Fixed — upgrade if you still see these

**Call to action:** [Download Latest installer](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe) → install → **re-paste your license key once**.

| Issue | Status |
|-------|--------|
| "Link jobs" Internal Server Error | Fixed in beta.6 |
| SCPRO key won't activate on empty desktop DB | Fixed — cohort keys seeded at boot |
| YouTube publish / OAuth broken on desktop | Fixed — per-install secrets |
| White screen / blank window on launch | Fixed — writable-path fail-fast; if the engine truly can't write, you now get a clear error page with a log link, not a blank window (beta.7+) |

Still on beta.5–beta.8? Upgrade to beta.9 (fixes engine Retry on the startup-error page).

---

## By design for this beta

| Area | What to expect |
|------|----------------|
| TikTok publish | Inbox / drafts only — finish in the TikTok app |
| TikTok URL download | Some networks get an **IP block** from TikTok (yt-dlp). qClip fails fast with a clear error. Workaround: **upload the file**, use a non-TikTok URL, or retry from another network/VPN. Not a desktop bug. |
| Instagram | Not supported |
| macOS Gatekeeper | Unsigned `.dmg` — right-click → **Open** / Privacy & Security → **Open Anyway** |
| macOS notarization | Not notarized yet — Gatekeeper warning is expected |
| macOS universal DMG | Prefer `qClip-mac-universal.dmg`; rebuild on Mac if only `arm64` is on the release |
| SmartScreen | Unsigned — **More info → Run anyway** |
| First-run models | ~1.5 GB download once |
| CPU desktop speed | Slow vs GPU — prefer short sources for feedback |
| GPU / Docker acceleration | Windows `.exe` uses GPU when the PC has one; Mac Docker is CPU-only. Stuck or unexpected speed → [Troubleshooting](tutorials/TUTORIAL_TROUBLESHOOTING.md) |
| Scheduled publish | Fires only while the desktop app is open |

---

## Need a step-by-step fix?

→ [Troubleshooting](tutorials/TUTORIAL_TROUBLESHOOTING.md)  
→ [FAQ](BETA_FAQ.md)

Report issues via the **[GitHub beta bug template](https://github.com/WheresWellium/StreamClip/issues/new?template=beta-bug.yml)** (include OS, `job_id`, short steps). Packaged desktop routes Help → Report a bug to the henna support collector when SMTP is configured on Vercel (F13).

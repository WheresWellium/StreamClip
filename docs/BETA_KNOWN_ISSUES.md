# Known issues (operator notes)

> **Creators:** use the public page — [Download & how to use](index.md) (henna home). This file is **not published**.

**Updated:** 2026-08-03 · Current build: **v1.0.0-beta.23** (Windows + Mac Apple Silicon)

---

## Fixed — upgrade if you still see these

**Call to action:** [Download Latest installer](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe) → install → **re-paste your license key once**.

| Issue | Status |
|-------|--------|
| "Link jobs" Internal Server Error | Fixed in beta.6 |
| SCPRO key won't activate on empty desktop DB | Fixed — cohort keys seeded at boot |
| YouTube publish / OAuth broken on desktop | Fixed — per-install secrets |
| White screen / blank window on launch | Fixed — writable-path fail-fast; if the engine truly can't write, you now get a clear error page with a log link, not a blank window (beta.7+) |
| Partial job fail toasted as “Job complete”; Edit blocked | Fixed in beta.22 — honest “Completed with errors” + Edit/Regenerate on failed clips |
| Support reports never left the device (F13) | Fixed — packaged Help → Report → GitHub Issues on [Project #4](https://github.com/users/WheresWellium/projects/4) |
| Virality blank when Ollama down | Fixed — local heuristic score + source badge |

Still on beta.5–beta.8? Upgrade to Latest (fixes engine Retry on the startup-error page).

---

## By design for this beta

| Area | What to expect |
|------|----------------|
| TikTok publish | Inbox / drafts only — finish in the TikTok app |
| TikTok URL download | Some networks get an **IP block** from TikTok (yt-dlp). qClip fails fast with a clear error. Workaround: **upload the file**, use a non-TikTok URL, or retry from another network/VPN. Not a desktop bug. |
| Instagram | Not supported |
| macOS Gatekeeper | Unsigned `.dmg` on Latest — right-click → **Open** / Privacy & Security → **Open Anyway** |
| macOS notarization | Not notarized yet — Gatekeeper warning is expected |
| macOS Intel | Latest ships Apple Silicon (`qClip-mac-arm64.dmg`); Intel needs a local universal rebuild |
| SmartScreen | Unsigned until EV cert — **More info → Run anyway** |
| First-run models | ~1.5 GB download once |
| CPU desktop speed | Slow vs GPU — prefer short sources for feedback |
| GPU / Docker acceleration | Windows `.exe` uses GPU when the PC has one; Mac Docker is CPU-only. Stuck or unexpected speed → [Troubleshooting](tutorials/TUTORIAL_TROUBLESHOOTING.md) |
| Scheduled publish | Fires only while the desktop app is open |

---

## Operator ship gates (not end-user bugs)

| Gate | Status |
|------|--------|
| Clean-VM install → first clip | Manual checklist — [CLEAN_DESKTOP_VM_VERIFY.md](CLEAN_DESKTOP_VM_VERIFY.md) |
| EV Authenticode / SmartScreen | Blocked on cert purchase — [DESKTOP_SIGNING.md](DESKTOP_SIGNING.md) |

---

## Need a step-by-step fix?

→ [Troubleshooting](tutorials/TUTORIAL_TROUBLESHOOTING.md)  
→ [FAQ](BETA_FAQ.md)

Prefer in-app **Help → Report a bug** / **Beta feedback** (lands on GitHub + Project #4). Backup: the **[GitHub beta bug template](https://github.com/WheresWellium/StreamClip/issues/new?template=beta-bug.yml)** (include OS, `job_id`, short steps).

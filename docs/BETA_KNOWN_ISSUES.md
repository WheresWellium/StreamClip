# Known issues

**Updated:** 2026-07-28 · Current Windows build: **v1.0.0-beta.6**

---

## Fixed — upgrade if you still see these

**Call to action:** [Download Latest installer](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe) → install → **re-paste your license key once**.

| Issue | Status |
|-------|--------|
| "Link jobs" Internal Server Error | Fixed in beta.6 |
| SCPRO key won't activate on empty desktop DB | Fixed — cohort keys seeded at boot |
| YouTube publish / OAuth broken on desktop | Fixed — per-install secrets |

Still on beta.5? Upgrade, or click **Skip** on Link jobs until you do.

---

## By design for this beta

| Area | What to expect |
|------|----------------|
| TikTok | Inbox / drafts only — finish in the TikTok app |
| Instagram | Not supported |
| macOS `.dmg` | Not public — use [Docker install](BETA_DOWNLOAD.md#macos-docker-no-public-dmg-yet) |
| SmartScreen | Unsigned — **More info → Run anyway** |
| First-run models | ~1.5 GB download once |
| CPU desktop speed | Slow vs GPU — prefer short sources for feedback |
| Scheduled publish | Fires only while the desktop app is open |

---

## Need a step-by-step fix?

→ [Troubleshooting](tutorials/TUTORIAL_TROUBLESHOOTING.md)  
→ [FAQ](BETA_FAQ.md)

Report issues in-app: **Help → Report a bug** (include OS, `job_id`, short steps).

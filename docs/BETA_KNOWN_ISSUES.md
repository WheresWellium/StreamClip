# qClip — Beta Known Issues

**Audience:** Phase 0–2 beta testers · **Owner:** core team  
**Last updated:** 2026-07-28 (beta.6)  
**Exit criteria:** [Beta test plan §4.5](BETA_TESTER_PLAN.md#45-exit-criteria-phase-1) · evidence pack [BETA_COHORT_EXIT.md](BETA_COHORT_EXIT.md)

---

## Fixed in beta.6 (upgrade if you still hit these)

Install **[v1.0.0-beta.6](https://github.com/WheresWellium/StreamClip/releases/latest/download/qClip-Setup-win-x64.exe)** and re-paste your license key once.

| Issue | Notes |
|-------|--------|
| "Link jobs" Internal Server Error | SQLite timestamp fix (`0014`) |
| SCPRO key won't activate on desktop | Cohort hashes seeded at boot |
| YouTube publish / OAuth fails on desktop | Per-install Fernet + auth secrets |

Still on **beta.5**? Upgrade, or click **Skip** on Link jobs until you upgrade.

---

## Platform limits (by design for beta)

| Area | Behavior |
|------|----------|
| TikTok | Off by default. When enabled: **inbox upload only** — finish posting in the TikTok app |
| YouTube Shorts | Supported with BYO Google OAuth + Pro/install license + **approved** clip. Desktop callback: `http://127.0.0.1:8765/.../youtube_shorts/callback` |
| Instagram | Not supported |
| Cloud multi-tenant | Not supported — self-host / desktop only |
| Lemon Squeezy keys | Network once on first activate if the key is not already local. **Desktop cohort (beta.6+):** paste in Settings → License only |
| Windows SmartScreen | Unsigned beta — **More info → Run anyway** |
| macOS `.dmg` | Not a public download yet — use [Docker self-host](BETA_DOWNLOAD.md#advanced-docker-self-host-operators) |
| First-run models | ~1.5 GB Whisper `medium` download on desktop |
| Scheduled publish | Fires only while the desktop app is running |
| Uploads | Up to 5 GiB on desktop; need free disk under AppData |

## Performance (informal)

| Scenario | GPU target | CPU target |
|----------|------------|------------|
| 1 h VOD → 5 clips | < 25 min | < ~110 min |
| API create-job (localhost) | < 500 ms | < 500 ms |

CPU-only desktop is **slow but supported**. Prefer shorter sources for beta feedback.

## Reporting bugs

**In-app:** **Help → Beta feedback** or **Report a bug**.  
Or reply to your invite email.

Include: OS, GPU, `job_id`, short log snippet, steps to reproduce.

Acceptance flows: [BETA_TESTER_PLAN.md](BETA_TESTER_PLAN.md) (T0 / T1 / T2).

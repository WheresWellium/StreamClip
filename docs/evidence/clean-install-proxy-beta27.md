# Clean-install proxy — beta.27 (not a Hyper-V VM substitute)

**Date (UTC):** 2026-08-04  
**Host:** build machine (AppData wiped + silent NSIS install) — Hyper-V unavailable without elevation  
**Installer:** `apps/desktop/release/qClip-Setup-win-x64.exe` → `%LOCALAPPDATA%\Programs\qClip`  
**Tag:** `v1.0.0-beta.27`

## Preflight

| Check | Result |
|-------|--------|
| Wipe `%LOCALAPPDATA%\StreamClip` | PASS |
| Silent install `/S` exit 0 | PASS |
| Packaged `desktop.yaml` has `twitch_client_id` | PASS |
| `latest.yml` version `1.0.0-beta.27` | PASS |

## Product path smokes (installed sidecar, PATH scrubbed of repo `bin/`)

| Source | Result | Job / notes |
|--------|--------|-------------|
| `upload-video` → done + ≥1 clip | **PASS** | `01KZ79CTD4MZ4KJ7E9YEVSKQQ3` — `tmp/smoke_matrix/upload-video-20260804-160302.log` |
| `twitch-clip` → done + ≥1 clip | **PASS** | `01KZ79FG6PPJDQE0B0QF2MP4WR` — `tmp/smoke_matrix/twitch-clip-20260804-160432.log` |
| Tester VOD `https://www.twitch.tv/videos/2836776596` | **PASS (download started)** | Job `01KZ79D6MTKXZ7W8CV6V5H4827`: log `ingest_download_start` + yt-dlp `.ytdl` / Frag* under throwaway data dir. Full 13h download→clips deferred (wall-clock). |

## Honest limits

- This is **not** a clean Windows 11 snapshot VM. It is the closest install-like gate on the build host.
- Manual UI steps (tray splash, license UI, in-app play) were **not** exercised here — API/sidecar path only.
- Operator still owes true clean-VM sign-off per `docs/CLEAN_DESKTOP_VM_VERIFY.md` if treating cohort exit as green.

## Sign-off (proxy)

```
Clean-install PROXY (not Hyper-V VM)
Installer: qClip-Setup-win-x64.exe  tag: v1.0.0-beta.27
Wipe AppData + silent install: PASS
Packaged twitch_client_id: PASS
upload-video done+clip: PASS (01KZ79CTD4MZ4KJ7E9YEVSKQQ3)
twitch-clip done+clip: PASS (01KZ79FG6PPJDQE0B0QF2MP4WR)
tester VOD download started (Client-ID path): PASS (01KZ79D6MTKXZ7W8CV6V5H4827)
True clean-VM UI gate: ☐ operator
Tester: agent (build host)  Date (UTC): 2026-08-04
```

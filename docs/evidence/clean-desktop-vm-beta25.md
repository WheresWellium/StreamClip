# Clean-desktop-VM evidence — v1.0.0-beta.25

**Installer:** https://github.com/WheresWellium/StreamClip/releases/tag/v1.0.0-beta.25  
**Local pack:** run `.\scripts\prepare_clean_desktop_vm.ps1 -Tag v1.0.0-beta.25` after publish  
**Template:** [CLEAN_DESKTOP_VM_VERIFY.md](../CLEAN_DESKTOP_VM_VERIFY.md)

## Automated (build host) — 2026-08-04

| Gate | Result |
|------|--------|
| Support → GitHub Project #4 (T85–T90) | Code + henna live (`project_configured`) |
| Matrix / e2e honesty (T80–T83) | pipeline_green + full e2e wired |
| `verify_desktop_release.ps1` (unsigned) | Run after cut if rechecking |

This is **not** a substitute for the clean-VM product gate (O4d).

## Manual clean Win11 VM — OPERATOR FILL

```
Clean-desktop-VM verify (product gate)
VM: Windows 11 __________  Snapshot: __________
Installer: qClip-Setup-win-x64.exe  build/tag: v1.0.0-beta.25
verify_desktop_clean.ps1: ☐ (build host)
Install + first launch (no white screen): ☐
License activate: ☐
Short source -> first clip: ☐   (job_id: __________)
Help → Report a bug lands on GitHub Project #4: ☐
Clip download: ☐
Restart persistence: ☐
Upgrade-from-previous: ☐ / N/A
Tester: __________  Date (UTC): __________
```

Do not invent Pass.

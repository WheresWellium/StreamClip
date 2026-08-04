# Clean-desktop-VM evidence — v1.0.0-beta.24

**Installer:** https://github.com/WheresWellium/StreamClip/releases/tag/v1.0.0-beta.24  
**Local pack:** `tmp/clean-vm-pack/qClip-Setup-win-x64.exe` (via `scripts/prepare_clean_desktop_vm.ps1`)  
**SHA256:** `D302A3810E9857FFFEB432B57C6E62412D0BC40FC94C9CD45326A360C2B7A6EF`  
**Template:** [CLEAN_DESKTOP_VM_VERIFY.md](../CLEAN_DESKTOP_VM_VERIFY.md)

## Automated (build host) — 2026-08-03

| Gate | Result |
|------|--------|
| Create-option pipeline matrix (180 cells) | PASS — [matrix-pipeline-timing-beta24.md](matrix-pipeline-timing-beta24.md) |
| `verify_desktop_release.ps1` (unsigned) | PASS |
| Seam coverage F10 | PASS (included in release gate) |
| Upgrade simulation F5 | PASS |
| `verify_desktop_clean.ps1` F1/F12 | PASS |
| Signing `-RequireSigning` | FAIL expected (no EV cert — O11) |

This is **not** a substitute for the clean-VM product gate (O4d).

## Manual clean Win11 VM — OPERATOR FILL

```
Clean-desktop-VM verify (product gate)
VM: Windows 11 __________  Snapshot: __________
Installer: qClip-Setup-win-x64.exe  build/tag: v1.0.0-beta.24
verify_desktop_clean.ps1: PASS (build host preflight)
Install + first launch (no white screen): ☐
License activate: ☐
Short source -> first clip: ☐   (job_id: __________)
Clip download: ☐
Restart persistence: ☐
Upgrade-from-previous: ☐ / N/A
Tester: __________  Date (UTC): __________
```

Paste completed rows above (or replace this section) when the VM run finishes. Do not invent Pass.

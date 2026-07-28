# qClip v1.0.0-beta.6 — release notes (draft)

Use when Phase A (+ B) of [DESKTOP_SOLO_GATE.md](DESKTOP_SOLO_GATE.md) pass, then tag.

## Highlights

- Desktop-solo product path (Windows + macOS) — **no Docker** for creators
- Windows: `qClip-Setup-win-x64.exe` + `latest.yml`
- macOS: `qClip-mac-arm64.dmg` (Apple Silicon; unsigned builds need right-click → Open)
- Invite kit: `./scripts/package_desktop_solo_kit.sh`

## Operator publish steps

```powershell
# After merge to master and smoke PASS:
# 1. Bump apps/desktop/package.json version to 1.0.0-beta.6
# 2. Tag and push (triggers .github/workflows/desktop-release.yml)
git tag v1.0.0-beta.6
git push origin v1.0.0-beta.6

# 3. Or: .\scripts\publish_desktop_release.ps1 -Version 1.0.0-beta.6
# 4. Update docs/BETA_DOWNLOAD.md banner + redeploy henna
```

## Tester notes

- SmartScreen / Gatekeeper expected until EV + notarization ([DESKTOP_SIGNING.md](DESKTOP_SIGNING.md))
- Logs: `%LOCALAPPDATA%\qClip\logs\` / `~/Library/Application Support/qClip/logs/`

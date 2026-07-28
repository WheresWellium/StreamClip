# Desktop signing & notarization (operator)

Scripts and secrets for Authenticode (Windows) and Developer ID + notarization (macOS).  
Detail (in-repo, not on henna nav): `packaging/installer/README.md` · `packaging/installer/MACOS.md`. End-user Mac notes: [MACOS_INSTALLER.md](MACOS_INSTALLER.md).

**Policy:** Signing is **not required** for the first internal solo beta (unsigned + SmartScreen / Gatekeeper workarounds are documented). Signing **is required** before a wide cohort or public-quality release.

---

## Windows (Authenticode / SmartScreen)

| Variable | Purpose |
|----------|---------|
| `CSC_LINK` | Path to `.pfx` **or** base64-encoded PFX (CI) |
| `CSC_KEY_PASSWORD` | PFX password |
| `SIGNTOOL` | Optional; auto-discovered from Windows SDK |
| `SIGN_TIMESTAMP_URL` | Optional; default DigiCert timestamp |

### Preflight

```powershell
.\scripts\verify_desktop_signing_ready.ps1
# Fail closed when shipping signed:
.\scripts\verify_desktop_signing_ready.ps1 -RequireSigning
```

Unset `CSC_*` → WARN + unsigned path OK. With `-RequireSigning`, missing secrets exit 1.

### Sign an artifact

```powershell
$env:CSC_LINK = "C:\secure\qclip-ev.pfx"
$env:CSC_KEY_PASSWORD = "<pfx-password>"
.\scripts\sign_windows_artifact.ps1 -Path apps\desktop\release\qClip-Setup-win-x64.exe
# Verify only:
.\scripts\sign_windows_artifact.ps1 -Path apps\desktop\release\qClip-Setup-win-x64.exe -VerifyOnly
```

electron-builder also signs when `CSC_*` are set during `build_desktop_installer.ps1`. CI maps `WINDOWS_CSC_LINK` / `WINDOWS_CSC_KEY_PASSWORD` → `CSC_*` (see installer README).

### SmartScreen notes

- **Unsigned:** “Windows protected your PC” → **More info → Run anyway** (expected for solo beta).
- **OV:** reputation builds with download volume; early installs may still warn.
- **EV:** usually establishes reputation faster; keep the same publisher identity across releases.

---

## macOS (Developer ID + notarization)

| Variable | Purpose |
|----------|---------|
| `CSC_NAME` | Keychain identity (alt to file) |
| `CSC_LINK` / `CSC_KEY_PASSWORD` | `.p12` path + password |
| `APPLE_ID` + `APPLE_APP_SPECIFIC_PASSWORD` + `APPLE_TEAM_ID` | notarytool password auth |
| `APPLE_API_KEY` + `APPLE_API_KEY_ID` + `APPLE_API_ISSUER` | App Store Connect API key auth |

Unset Apple credentials → unsigned DMG; Gatekeeper: **right-click → Open**.

### Notarize

Requires a Developer ID–signed `.dmg` / `.app` on a macOS host with Xcode CLT:

```bash
./scripts/notarize_macos_artifact.sh apps/desktop/release/qClip-mac-arm64.dmg
```

Skips cleanly (exit 0) when neither password nor API-key auth is set. On success: submits via `notarytool`, waits, staples, validates.

Build path: `./scripts/build_desktop_installer_macos.sh` — see [MACOS_INSTALLER.md](MACOS_INSTALLER.md).

---

## When to flip from unsigned → signed

| Stage | Signing |
|-------|---------|
| Internal solo beta | Optional (current path) |
| Wide cohort / public download | Required (Windows EV/OV + macOS Developer ID + notarize) |

Checklist: [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).

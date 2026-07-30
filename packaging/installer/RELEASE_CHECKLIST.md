# Desktop release checklist (§4.10 Windows + §5 macOS)

Use before tagging `v*` for GitHub Releases. Windows EV signing is ready to run;
the remaining blocker is buying/receiving the certificate and installing the CI
secrets or local PFX.

**Canonical EV / SmartScreen runbook:** [`docs/DESKTOP_SIGNING.md`](../../docs/DESKTOP_SIGNING.md)
(prerequisites, unsigned vs signed paths, script flags, CI, dry-runs).

## Windows EV signing prep

1. Buy a Microsoft-trusted **EV Code Signing** certificate. Practical operator
   options: DigiCert EV Code Signing, Sectigo EV Code Signing, GlobalSign EV Code
   Signing, SSL.com EV Code Signing. Prefer the vendor's cloud/HSM flow if it can
   still export or expose a PFX-compatible signing path for electron-builder; if
   the vendor only provides a USB token, plan to sign locally on the release
   workstation instead of GitHub Actions.
2. Complete organization validation using the exact publisher identity that should
   appear in Windows ("StreamClip", "Jet Stream", or legal entity). Keep this
   identity stable across releases; SmartScreen reputation is tied to publisher
   identity and signed binaries.
3. Export or provision the signing credential as a `.pfx` plus strong password
   where possible. Store the PFX outside the repo, for example
   `C:\secure\streamclip-ev.pfx`.
4. Install Windows SDK Build Tools on the local signing workstation so
   `signtool.exe` is available, or set `SIGNTOOL` to the full path.
5. Keep the current unsigned beta truth unchanged until the signed build ships:
   `docs/BETA_DOWNLOAD.md` says Latest (`v1.0.0-beta.6`) is unsigned and
   `docs/BETA_KNOWN_ISSUES.md` documents SmartScreen "More info -> Run anyway".

## Required signing variables

| Scope | Variable / secret | Value |
|-------|-------------------|-------|
| Local PowerShell | `CSC_LINK` | Path to local PFX, e.g. `C:\secure\streamclip-ev.pfx` |
| Local PowerShell | `CSC_KEY_PASSWORD` | PFX password |
| Local PowerShell | `SIGNTOOL` | Optional full path to `signtool.exe` if auto-discovery fails |
| Local PowerShell | `SIGN_TIMESTAMP_URL` | Optional timestamp URL; default is `http://timestamp.digicert.com` |
| GitHub Actions | `WINDOWS_CSC_LINK` | Base64 PFX content, or a path if the workflow stages the file |
| GitHub Actions | `WINDOWS_CSC_KEY_PASSWORD` | PFX password |

Create the CI `WINDOWS_CSC_LINK` secret from the operator machine:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\secure\streamclip-ev.pfx")) |
  Set-Clipboard
```

## Local first signed release

Run from `D:\Projects\streamclip` only.

```powershell
$env:CSC_LINK = "C:\secure\streamclip-ev.pfx"
$env:CSC_KEY_PASSWORD = "<pfx-password>"
$env:STREAMCLIP_REQUIRE_SIGNED_INSTALLER = "1"

.\scripts\verify_desktop_signing_ready.ps1 -RequireSigning
.\scripts\verify_desktop.ps1
.\scripts\build_desktop_installer.ps1
.\scripts\sign_windows_artifact.ps1 -Path apps\desktop\release\qClip-Setup-win-x64.exe -VerifyOnly
```

Expected artifacts:

- `apps/desktop/release/qClip-Setup-win-x64.exe`
- `apps/desktop/release/latest.yml`

The build script calls `enable_electron_signing.ps1 -Mode Auto`; when `CSC_*` is
set, it enables `apps/desktop/package.json` `build.win.signAndEditExecutable` so
electron-builder signs the app and NSIS installer during `npm run dist`.

## Verify Authenticode

```powershell
.\scripts\sign_windows_artifact.ps1 -Path apps\desktop\release\qClip-Setup-win-x64.exe -VerifyOnly
signtool verify /pa /v apps\desktop\release\qClip-Setup-win-x64.exe
Get-AuthenticodeSignature apps\desktop\release\qClip-Setup-win-x64.exe | Format-List
```

Pass criteria:

- `signtool verify /pa /v` exits 0.
- Publisher/subject matches the EV certificate organization.
- SHA256 digest and timestamp are present.
- `Get-AuthenticodeSignature` reports `Status: Valid`.

## CI signed release

1. Add GitHub Actions secrets `WINDOWS_CSC_LINK` and
   `WINDOWS_CSC_KEY_PASSWORD`.
2. Run the `Desktop release` workflow manually with:
   - `version`: the target version, e.g. `1.0.0-beta.6`
   - `require_signed`: `true`
3. Confirm the `Desktop signing preflight` step prints `CSC_* configured`.
4. Confirm the release draft contains both:
   - `qClip-Setup-win-x64.exe`
   - `latest.yml`
5. Download the draft asset on a clean Windows VM and run the Authenticode checks
   above before publishing the release.

If the EV provider requires a USB token or interactive hardware approval, use the
local first signed release path and upload with `publish_desktop_release.ps1`
after verification.

## Publish after verification

Do not publish until Authenticode verification passes.

```powershell
.\scripts\publish_desktop_release.ps1 -Version 1.0.0-beta.N -SkipBuild
```

`publish_desktop_release.ps1` uploads `qClip-Setup-win-x64.exe` and
`latest.yml`, then bumps `docs/BETA_DOWNLOAD.md` unless `-NoDocsBump` is set.
After a signed build ships, update the Windows row in `docs/BETA_DOWNLOAD.md` from
"unsigned; SmartScreen may warn" to the signed version and keep a short note that
SmartScreen reputation can still warm up during the first downloads.

## SmartScreen expectations

- Unsigned beta builds: warning is expected; document "More info -> Run anyway".
- Standard OV certificate: Authenticode is valid, but SmartScreen reputation may
  still require download volume.
- EV certificate: best path for initial reputation, but SmartScreen can still warn
  during reputation warm-up, certificate changes, or low-volume releases.
- Keep the same publisher identity and timestamp every release; do not rotate certs
  unless needed.

## Windows unsigned smoke path

For beta-only unsigned validation, leave `CSC_LINK` and `CSC_KEY_PASSWORD` unset:

1. `.\scripts\download_ffmpeg_windows.ps1` (idempotent; also auto-run by installer build)
2. `.\scripts\verify_desktop.ps1` -- db, storage, ffmpeg smoke
3. `.\scripts\build_desktop_installer.ps1` -- produces `qClip-Setup-win-x64.exe` + `latest.yml`
4. Confirm `apps/desktop/release/latest.yml` exists (electron-updater)
5. Do not publish as a signed release; keep SmartScreen caveat in beta docs.

## macOS `.dmg` (Mac host / `macos-latest` CI)

1. `./scripts/download_ffmpeg_macos.sh`
2. `./scripts/build_desktop_installer_macos.sh` (builds UI via `build_desktop_ui.sh`)
3. `./scripts/verify_desktop_installer_macos.sh apps/desktop/release/qClip-mac-universal.dmg`
4. Optional: Developer ID sign + notarize (`packaging/installer/MACOS.md`)
5. Bump `docs/BETA_DOWNLOAD.md` macOS row when a DMG ships

## CI

- `.github/workflows/desktop-release.yml`
  - **Windows job** — required; publishes Setup exe + `latest.yml`
  - **macOS job** — scaffold on `macos-latest` with `continue-on-error: true` until §5.2–5.3 (MPS wheels + notarization) are green

## Beta kit (Docker path)

```powershell
.\scripts\prepare_beta_kit.ps1 -Mode Source   # default runnable tree
.\scripts\prepare_beta_kit.ps1 -Mode ProdImages
```

Testers run `.\scripts\start_local.ps1` then `.\scripts\verify_stack.ps1`.

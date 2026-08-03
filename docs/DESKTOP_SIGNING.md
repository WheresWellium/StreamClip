# Windows EV Authenticode & SmartScreen (§4.10)

Canonical operator runbook for qClip Windows code signing.
Purchase of the EV certificate is **out of band** — this doc covers everything else.

**Do not invent or commit certificates.** Beta remains unsigned until a real EV (or OV) PFX is provisioned.

Related:

- Installer build overview: `packaging/installer/README.md` (repo root)
- Release tag checklist: `packaging/installer/RELEASE_CHECKLIST.md` (repo root)
- Tester SmartScreen copy: [`BETA_KNOWN_ISSUES.md`](./BETA_KNOWN_ISSUES.md) · [`BETA_DOWNLOAD.md`](./BETA_DOWNLOAD.md)
- CI: `.github/workflows/desktop-release.yml` (repo root)

---

## Status (ops truth)

| Item | State |
|------|--------|
| NSIS installer + electron-builder | ✅ Ready |
| Unsigned beta publish path | ✅ Ready (`1.0.0-beta.22` Latest target, 2026-08-03) |
| Signing scripts / CI preflight | ✅ Ready (`verify_desktop_signing_ready.ps1 -RequireSigning` fails closed without cert) |
| EV certificate purchased + installed | ❌ **Blocked** (operator purchase) — rechecked 2026-08-03: `CSC_THUMBPRINT` unset |
| First signed GitHub Release | ❌ Blocked on cert — do not run `-RequireSigned` until Path C/D credentials exist |
| SmartScreen reputation warm-up | ❌ After first signed release |

---

## Four paths (pick one — do not mix)

### A — Unsigned beta (current production truth)

Use when no signing credentials are set.

| Step | Command / action |
|------|------------------|
| Preflight (informational) | `.\scripts\verify_desktop_signing_ready.ps1` → prints unsigned OK |
| Dry-run matrix | `.\scripts\verify_desktop_signing_ready.ps1 -DryRun` |
| Build | `.\scripts\build_desktop_installer.ps1` |
| Publish | `.\scripts\publish_desktop_release.ps1 -Version 1.0.0-beta.N` |
| Docs | Keep “unsigned; SmartScreen may warn” on `BETA_DOWNLOAD.md` |

`build_desktop_installer.ps1` calls `enable_electron_signing.ps1 -Mode Auto`, which leaves
`apps/desktop/package.json` → `build.win.signAndEditExecutable: false` and sets
`CSC_IDENTITY_AUTO_DISCOVERY=false` so electron-builder does not require Developer Mode / winCodeSign symlinks.

**Never** set `STREAMCLIP_REQUIRE_SIGNED_INSTALLER=1` on this path.

### B — Signed via PFX (OV / exportable cloud HSM)

Use when the CA issued (or you can export) a `.pfx`. Rare for new EV after June 2023.

| Step | Command / action |
|------|------------------|
| Env | `$env:CSC_LINK = "C:\secure\streamclip-ev.pfx"` · `$env:CSC_KEY_PASSWORD = "..."` · `$env:STREAMCLIP_REQUIRE_SIGNED_INSTALLER = "1"` |
| Preflight (fail-closed) | `.\scripts\verify_desktop_signing_ready.ps1 -RequireSigning` |
| Build (electron-builder signs) | `.\scripts\build_desktop_installer.ps1` |
| Verify | `.\scripts\sign_windows_artifact.ps1 -Path apps\desktop\release\qClip-Setup-win-x64.exe -VerifyOnly` |
| Publish | `.\scripts\publish_desktop_release.ps1 -Version 1.0.0-beta.N -SkipBuild -RequireSigned` |

Encode PFX for CI (operator machine only — never commit):

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\secure\streamclip-ev.pfx")) | Set-Clipboard
# → GitHub secrets WINDOWS_CSC_LINK + WINDOWS_CSC_KEY_PASSWORD
```

### C — Signed via EV USB token / HSM thumbprint (**post-2023 EV norm**)

Since June 2023, new code-signing certs (OV and EV) must live on FIPS 140-2 Level 2+
hardware — the private key **cannot** leave the token as a PFX. This is the default
EV path. Sign on a **local Windows release workstation** (token plugged in), not on
GitHub-hosted runners.

| Step | Command / action |
|------|------------------|
| 1. Buy EV | DigiCert / Sectigo / GlobalSign / SSL.com — ask for **USB token or cloud HSM** that installs into the Windows cert store |
| 2. Install middleware | Vendor SafeNet/eToken drivers; plug token; unlock PIN |
| 3. Copy thumbprint | `Get-ChildItem Cert:\CurrentUser\My \| Where-Object { $_.HasPrivateKey } \| Format-List Subject,Thumbprint` |
| 4. Env | `$env:CSC_THUMBPRINT = "<40-hex-SHA1>"` · `$env:STREAMCLIP_REQUIRE_SIGNED_INSTALLER = "1"` |
| 5. Preflight | `.\scripts\verify_desktop_signing_ready.ps1 -RequireSigning` (must find thumbprint in store) |
| 6. Build unsigned | `.\scripts\build_desktop_installer.ps1` (electron-builder leaves PE unsigned; token keys are not CSC_LINK) |
| 7. Post-sign | `.\scripts\sign_windows_artifact.ps1 -Path apps\desktop\release\qClip-Setup-win-x64.exe` |
| 8. Verify | `.\scripts\sign_windows_artifact.ps1 -Path … -VerifyOnly` → `Status: Valid` |
| 9. Publish | `.\scripts\publish_desktop_release.ps1 -Version 1.0.0-beta.N -SkipBuild -RequireSigned` |

One-liner after purchase:

```powershell
$env:CSC_THUMBPRINT = "<paste-40-hex>"
$env:STREAMCLIP_REQUIRE_SIGNED_INSTALLER = "1"
.\scripts\verify_desktop_signing_ready.ps1 -RequireSigning
.\scripts\build_desktop_installer.ps1
.\scripts\sign_windows_artifact.ps1 -Path apps\desktop\release\qClip-Setup-win-x64.exe
.\scripts\publish_desktop_release.ps1 -Version 1.0.0-beta.6 -SkipBuild -RequireSigned
```

### D — Azure Trusted Signing (recommended modern alternative)

Microsoft cloud HSM signing — **no USB token**, CI-friendly, ~$10/mo Basic tier.
Eligibility (as of late 2025): US/Canada orgs with ≥3 years business history (check
current Azure docs — criteria expand over time). Reputation builds like OV; short-lived
certs rotate automatically (unaffected by the ~460-day CA max validity from March 2026).

| Step | Action |
|------|--------|
| 1 | Create Azure Trusted Signing account + certificate profile |
| 2 | App registration → set `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` |
| 3 | Configure electron-builder `win.sign` / `azureSignOptions` (endpoint, account, profile) — see [electron-builder Windows signing](https://www.electron.build/docs/features/code-signing/code-signing-win/) |
| 4 | Build + publish as usual; verify with `sign_windows_artifact.ps1 -VerifyOnly` |

Path D is **not** wired through `CSC_THUMBPRINT` / `CSC_LINK` — it uses Azure env vars
and electron-builder’s azure signer. Prefer Path D for CI; Path C for a one-off EV token.

---

## Prerequisites (before first signed build)

1. **Choose Path C (EV token) or Path D (Azure Trusted Signing).** New EV cannot be a
   free-floating PFX on disk (CA/B Forum June 2023). Path B only if your CA still
   exports via an approved cloud HSM.
2. **Stable publisher identity** — legal entity name that appears in Authenticode.
   SmartScreen reputation is publisher-bound; do not rename later.
3. **Windows SDK Build Tools** so `signtool.exe` is discoverable (or set `SIGNTOOL`).
4. **Expected cost / timeline (2026 ballpark):** EV token ~$400–700/yr + 1–10 day org
   validation; Azure Trusted Signing ~$9.99/mo + Azure identity verification.
5. **Cert validity:** public code-signing certs max ~460 days from March 2026 — plan
   renewals; Azure rotates automatically.

---

## Environment & script flags

| Name | Scope | Purpose |
|------|-------|---------|
| `CSC_THUMBPRINT` | Local (Path C) | 40-hex SHA1 of EV cert in Windows store |
| `CSC_LINK` | Local / CI (Path B) | Path to `.pfx` **or** base64 PFX content |
| `CSC_KEY_PASSWORD` | Local / CI (Path B) | PFX password |
| `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` | CI (Path D) | Azure Trusted Signing app credentials |
| `SIGNTOOL` | Local | Optional full path to `signtool.exe` |
| `SIGN_TIMESTAMP_URL` | Local | Default `http://timestamp.digicert.com` |
| `STREAMCLIP_REQUIRE_SIGNED_INSTALLER=1` | Local / CI | Fail build/preflight if signing credentials missing |
| `WINDOWS_CSC_LINK` | GitHub secret | Mapped to `CSC_LINK` in `desktop-release.yml` |
| `WINDOWS_CSC_KEY_PASSWORD` | GitHub secret | Mapped to `CSC_KEY_PASSWORD` |
| `CSC_IDENTITY_AUTO_DISCOVERY` | Set by scripts | `false` unsigned · `true` when CSC_* present |

### Scripts

| Script | Flags | Notes |
|--------|-------|-------|
| `verify_desktop_signing_ready.ps1` | `-RequireSigning`, `-DryRun` | Accepts `CSC_THUMBPRINT` **or** `CSC_LINK`+password; fail-closed when requiring signed |
| `enable_electron_signing.ps1` | `-Mode Auto\|Enable\|Disable`, `-DryRun` | Auto toggles `signAndEditExecutable`; dry-run does **not** write `package.json` |
| `sign_windows_artifact.ps1` | `-Path`, `-Thumbprint`, `-VerifyOnly`, `-DryRun` | Path C post-build Authenticode; Path B PFX; verify-only |
| `build_desktop_installer.ps1` | (build switches) | Honors `STREAMCLIP_REQUIRE_SIGNED_INSTALLER`; electron-builder signs only when CSC_LINK set |
| `publish_desktop_release.ps1` | `-Version`, `-SkipBuild`, `-PublishOnly`, `-NoDocsBump`, `-RequireSigned`, `-DryRun` | `-RequireSigned` refuses upload if Authenticode ≠ Valid |

---

## CI (`Desktop release` workflow)

1. Add secrets `WINDOWS_CSC_LINK` + `WINDOWS_CSC_KEY_PASSWORD`.
2. Manual run (`workflow_dispatch`):
   - `version`: e.g. `1.0.0-beta.6`
   - `require_signed`: **`true`** for the first EV ship (fails if secrets missing)
3. Confirm step **Desktop signing preflight** prints `CSC_* configured`.
4. Workflow publishes a **draft** release on `workflow_dispatch` — download the Setup exe on a clean Windows VM and verify before publishing.
5. Tag pushes (`v*`) still build; without secrets the installer stays unsigned (beta-safe default).

If the CA requires an interactive USB token / hardware approval, **do not** use GitHub-hosted runners — use local Path B + `publish_desktop_release.ps1 -SkipBuild -RequireSigned`.

---

## Authenticode pass criteria

```powershell
.\scripts\sign_windows_artifact.ps1 -Path apps\desktop\release\qClip-Setup-win-x64.exe -VerifyOnly
signtool verify /pa /v apps\desktop\release\qClip-Setup-win-x64.exe
Get-AuthenticodeSignature apps\desktop\release\qClip-Setup-win-x64.exe | Format-List *
```

Must show:

- `signtool verify /pa` exit 0
- Publisher/subject matches EV org identity
- SHA256 digest + trusted timestamp present
- `Get-AuthenticodeSignature` → `Status: Valid`

Artifacts to ship: `qClip-Setup-win-x64.exe` + `latest.yml` (electron-updater).

---

## SmartScreen expectations

| Build | What testers see |
|-------|------------------|
| Unsigned beta | “Windows protected your PC” — **More info → Run anyway** (documented) |
| OV signed | Valid Authenticode; SmartScreen may still warn until download reputation accumulates |
| EV signed | Best initial reputation; still can warn during warm-up, cert change, or low volume |

Rules of the road:

- Keep the **same publisher identity** across releases.
- Always **timestamp** signatures (default DigiCert URL).
- Signing ≠ permanent SmartScreen silence; warm-up takes real downloads.
- After first signed ship, update `BETA_DOWNLOAD.md` / known-issues copy (deploy-owner chat — avoid parallel edits).

---

## Operator dry-run (no cert yet)

Safe on any workstation; does not publish or require a PFX:

```powershell
cd D:\Projects\streamclip
.\scripts\verify_desktop_signing_ready.ps1 -DryRun
.\scripts\enable_electron_signing.ps1 -Mode Auto -DryRun
.\scripts\publish_desktop_release.ps1 -Version 1.0.0-beta.6 -SkipBuild -DryRun
```

Expect: unsigned path OK, `signAndEditExecutable` would stay `false`, publish dry-run reports installer presence + signature status without calling `gh`.

---

## First signed release checklist (when cert arrives)

1. Choose **Path C** (paste thumbprint) or **Path D** (Azure) or **Path B** (PFX if available).
2. `verify_desktop_signing_ready.ps1 -RequireSigning` → green.
3. Build; Path C → `sign_windows_artifact.ps1` then `-VerifyOnly` → Valid.
4. `publish_desktop_release.ps1 … -RequireSigned` (or CI `require_signed: true` + promote draft).
5. Clean-VM install: SmartScreen may still warm up — note in release notes.
6. Deploy owner updates `BETA_DOWNLOAD.md` Windows row to signed wording.
7. Mark MASTER §4.10 remaining work closed when the signed asset is live.

# Sign a Windows PE binary with Authenticode (§4.10).
# Canonical runbook: docs/DESKTOP_SIGNING.md
#
# Two credential modes (post-June-2023 CA/B rules make mode 2 the EV norm):
#   1. PFX file:          CSC_LINK + CSC_KEY_PASSWORD (OV certs / legacy exports)
#   2. Cert-store SHA1:   CSC_THUMBPRINT (EV USB token / HSM middleware installs
#                         the cert into the Windows store; key never leaves hardware)
#
#   .\scripts\sign_windows_artifact.ps1 -Path apps\desktop\release\qClip-Setup-win-x64.exe
#   .\scripts\sign_windows_artifact.ps1 -Path ... -Thumbprint <40-hex-sha1>
#   .\scripts\sign_windows_artifact.ps1 -Path ... -VerifyOnly
#   .\scripts\sign_windows_artifact.ps1 -Path ... -DryRun
param(
    [Parameter(Mandatory = $true)]
    [string]$Path,
    [string]$CertificatePath = $env:CSC_LINK,
    [string]$CertificatePassword = $env:CSC_KEY_PASSWORD,
    [string]$Thumbprint = $env:CSC_THUMBPRINT,
    [string]$SignTool = $env:SIGNTOOL,
    [string]$TimestampUrl = $(if ($env:SIGN_TIMESTAMP_URL) { $env:SIGN_TIMESTAMP_URL } else { "http://timestamp.digicert.com" }),
    [switch]$VerifyOnly,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Path)) {
    Write-Error "File not found: $Path"
}

if ($Thumbprint) {
    $Thumbprint = $Thumbprint.Replace(" ", "").ToUpper()
    if ($Thumbprint -notmatch "^[0-9A-F]{40}$") {
        Write-Error "CSC_THUMBPRINT must be a 40-hex-char SHA1 thumbprint (got '$Thumbprint')"
    }
}

if (-not $VerifyOnly -and -not $DryRun) {
    if (-not $Thumbprint) {
        if (-not $CertificatePath) {
            Write-Error "Set CSC_THUMBPRINT (EV token/HSM) or CSC_LINK (PFX), or pass -Thumbprint / -CertificatePath"
        }
        if (-not $CertificatePassword) {
            Write-Error "Set CSC_KEY_PASSWORD or pass -CertificatePassword (PFX mode)"
        }
    }
}

function Test-ThumbprintInStore([string]$Sha1) {
    foreach ($store in @("Cert:\CurrentUser\My", "Cert:\LocalMachine\My")) {
        try {
            if (Get-ChildItem $store -ErrorAction SilentlyContinue |
                    Where-Object { $_.Thumbprint -eq $Sha1 }) { return $store }
        }
        catch { }
    }
    return $null
}

if (-not $SignTool) {
    $kitsRoot = "${env:ProgramFiles(x86)}\Windows Kits\10\bin"
    if (Test-Path $kitsRoot) {
        $SignTool = Get-ChildItem $kitsRoot -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match "\\x64\\" } |
            Sort-Object FullName -Descending |
            Select-Object -First 1 -ExpandProperty FullName
    }
}

if (-not $SignTool -or -not (Test-Path $SignTool)) {
    Write-Error "signtool.exe not found. Install Windows SDK or set SIGNTOOL."
}

if ($DryRun) {
    Write-Host "=== Authenticode dry-run ===" -ForegroundColor Cyan
    Write-Host "Target:     $Path"
    Write-Host "signtool:   $SignTool"
    Write-Host "Timestamp:  $TimestampUrl"
    $certOk = $false
    if ($Thumbprint) {
        $store = Test-ThumbprintInStore -Sha1 $Thumbprint
        if ($store) {
            Write-Host "CSC_THUMBPRINT: $Thumbprint found in $store (token/HSM mode)"
            $certOk = $true
        } else {
            Write-Host "CSC_THUMBPRINT: $Thumbprint NOT in cert store - plug in the EV token / install CA middleware" -ForegroundColor Yellow
        }
    }
    elseif ($CertificatePath) {
        if (Test-Path -LiteralPath $CertificatePath) {
            Write-Host "CSC_LINK:   file $CertificatePath"
            $certOk = $true
        } elseif ($CertificatePath.Length -gt 256) {
            Write-Host "CSC_LINK:   base64 PFX (length $($CertificatePath.Length)) - decode to a temp file before signtool /f"
            $certOk = $true
        } else {
            Write-Host "CSC_LINK:   set but not a file path or base64 blob" -ForegroundColor Yellow
        }
    } else {
        Write-Host "CSC_LINK:   (unset)" -ForegroundColor Yellow
    }
    if (-not $CertificatePassword) {
        Write-Host "CSC_KEY_PASSWORD: (unset)" -ForegroundColor Yellow
    } else {
        Write-Host "CSC_KEY_PASSWORD: (set)"
    }
    try {
        $sig = Get-AuthenticodeSignature -FilePath $Path
        Write-Host ("Current Status: {0}" -f $sig.Status)
        if ($sig.SignerCertificate) {
            Write-Host ("Publisher:      {0}" -f $sig.SignerCertificate.Subject)
        }
    } catch {
        Write-Host "Current Status: (could not read Authenticode)" -ForegroundColor Yellow
    }
    if ($VerifyOnly) {
        Write-Host "Would run: signtool verify /pa /v `"$Path`""
    } elseif ($Thumbprint -and $certOk) {
        Write-Host "Would run: signtool sign /fd SHA256 /tr ... /td SHA256 /sha1 $Thumbprint `"$Path`" then verify"
    } elseif ($certOk -and $CertificatePassword) {
        Write-Host "Would run: signtool sign /fd SHA256 /tr ... /f <pfx> `"$Path`" then verify"
    } else {
        Write-Host "Would NOT sign - missing/unresolvable CSC_* (use -VerifyOnly to check an existing signature)." -ForegroundColor Yellow
    }
    Write-Host "Dry-run complete (no sign/verify executed)." -ForegroundColor Green
    exit 0
}

if (-not $VerifyOnly) {
    Write-Host "Signing $Path ..." -ForegroundColor Cyan
    if ($Thumbprint) {
        $store = Test-ThumbprintInStore -Sha1 $Thumbprint
        if (-not $store) {
            Write-Error "Certificate $Thumbprint not found in CurrentUser/LocalMachine My store. Plug in the EV token and install the CA middleware (SafeNet Authentication Client etc.), then retry."
        }
        # Key stays on the token/HSM; middleware prompts for the PIN.
        & $SignTool sign /fd SHA256 /tr $TimestampUrl /td SHA256 /sha1 $Thumbprint $Path
    }
    else {
        if ($CertificatePath.Length -gt 256 -and -not (Test-Path -LiteralPath $CertificatePath)) {
            Write-Error "CSC_LINK looks like base64; write it to a .pfx file for signtool /f, or let electron-builder sign during dist."
        }
        & $SignTool sign /fd SHA256 /tr $TimestampUrl /td SHA256 /f $CertificatePath /p $CertificatePassword $Path
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "Verifying signature ..." -ForegroundColor Cyan
& $SignTool verify /pa /v $Path
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Signature applied and verified." -ForegroundColor Green

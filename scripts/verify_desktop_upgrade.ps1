# Desktop upgrade simulation (F5 pre-flight).
#
# Simulates the DB half of an in-place upgrade WITHOUT a full install:
#   1. Create a SQLite DB stamped at an OLDER migration revision (as an old build left it).
#   2. Insert a marker row (a job) so we can prove data survives.
#   3. Boot the sidecar against that same data dir -> it runs `alembic upgrade head`.
#   4. Assert the sidecar becomes healthy AND the marker row still exists.
#
# This guards taxonomy F5 (migrate/boot fail after update). See
# docs/DESKTOP_UPGRADE_MATRIX.md for the full (manual) matrix.
param(
    [string]$FromRevision = "0012_license_activation_seats",
    [int]$Port = 8798
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Snapshot env we mutate so this script is hermetic when chained (no leak into
# sibling verify scripts — the cause of a cross-gate port/data-dir collision).
$_envKeys = @(
    "STREAMCLIP_DESKTOP_DATA_DIR", "STREAMCLIP_SIDECAR_PORT",
    "STREAMCLIP_SIDECAR_SKIP_PREFETCH", "STREAMCLIP_DATABASE__URL",
    "STREAMCLIP_DATABASE__SYNC_URL"
)
$_envSaved = @{}
foreach ($k in $_envKeys) { $_envSaved[$k] = [Environment]::GetEnvironmentVariable($k) }
function Restore-Env {
    foreach ($k in $script:_envKeys) {
        if ($null -eq $script:_envSaved[$k]) {
            Remove-Item "Env:$k" -ErrorAction SilentlyContinue
        } else {
            Set-Item "Env:$k" $script:_envSaved[$k]
        }
    }
}
function Exit-Restored([int]$code) { Restore-Env; exit $code }

$dataDir = Join-Path ([System.IO.Path]::GetTempPath()) ("qclip-upgrade-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
$dbPath = (Join-Path $dataDir "streamclip.db")
$dbPosix = $dbPath -replace '\\', '/'

$env:STREAMCLIP_DESKTOP_DATA_DIR = $dataDir
$env:STREAMCLIP_SIDECAR_PORT = "$Port"
$env:STREAMCLIP_SIDECAR_SKIP_PREFETCH = "1"
$env:STREAMCLIP_DATABASE__URL = "sqlite+aiosqlite:///$dbPosix"
$env:STREAMCLIP_DATABASE__SYNC_URL = "sqlite:///$dbPosix"

Write-Host "=== Stage 1: create OLD-build DB at revision $FromRevision ===" -ForegroundColor Cyan
python -m alembic upgrade $FromRevision
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: could not stamp DB at $FromRevision." -ForegroundColor Red
    Remove-Item -Recurse -Force $dataDir -ErrorAction SilentlyContinue
    Exit-Restored 1
}

Write-Host ""
Write-Host "=== Stage 2: insert a marker row (proves data survives upgrade) ===" -ForegroundColor Cyan
$marker = "upgrade-marker-" + [guid]::NewGuid().ToString("N").Substring(0, 8)
# Write the seed helper to a temp .py file — passing multi-line Python through
# `python -c` in PowerShell mangles newlines/f-strings.
$seedPy = Join-Path $dataDir "_seed_marker.py"
@"
import sqlite3, uuid
con = sqlite3.connect(r'$dbPath')
cur = con.cursor()
cols = [r[1] for r in cur.execute('PRAGMA table_info(jobs)').fetchall()]
jid = str(uuid.uuid4())
row = {'id': jid, 'status': 'done', 'display_title': '$marker'}
present = [c for c in row if c in cols]
placeholders = ', '.join('?' for _ in present)
cur.execute(f"INSERT INTO jobs ({', '.join(present)}) VALUES ({placeholders})", [row[c] for c in present])
con.commit()
con.close()
print(jid)
"@ | Set-Content -Encoding UTF8 $seedPy
$jobId = python $seedPy
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: could not seed marker job row." -ForegroundColor Red
    Remove-Item -Recurse -Force $dataDir -ErrorAction SilentlyContinue
    Exit-Restored 1
}
Write-Host "Seeded job $jobId with marker $marker"

Write-Host ""
Write-Host "=== Stage 3: boot sidecar (runs upgrade head) ===" -ForegroundColor Cyan
$sidecar = Start-Process -FilePath "python" -ArgumentList "-m", "desktop_sidecar" -PassThru -NoNewWindow
$healthy = $false
try {
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 2
        try {
            $res = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/health" -UseBasicParsing -TimeoutSec 3
            if ($res.StatusCode -eq 200) { $healthy = $true; break }
        } catch { }
        if ($sidecar.HasExited) { break }
    }
} finally {
    if (-not $sidecar.HasExited) { $sidecar | Stop-Process -Force }
}

if (-not $healthy) {
    Write-Host "FAIL: sidecar did not become healthy after upgrade from $FromRevision (F5)." -ForegroundColor Red
    Remove-Item -Recurse -Force $dataDir -ErrorAction SilentlyContinue
    Exit-Restored 1
}

Write-Host ""
Write-Host "=== Stage 4: assert marker row survived the upgrade ===" -ForegroundColor Cyan
$checkPy = Join-Path $dataDir "_check_marker.py"
@"
import sqlite3
con = sqlite3.connect(r'$dbPath')
n = con.execute("SELECT COUNT(*) FROM jobs WHERE display_title = '$marker'").fetchone()[0]
con.close()
print(n)
"@ | Set-Content -Encoding UTF8 $checkPy
$found = (python $checkPy).Trim()
Remove-Item -Recurse -Force $dataDir -ErrorAction SilentlyContinue

if ($found -ne "1") {
    Write-Host "FAIL: marker row not found after upgrade (data loss). Found=$found" -ForegroundColor Red
    Exit-Restored 1
}

Write-Host ""
Write-Host "Upgrade simulation PASSED: $FromRevision -> head, data preserved." -ForegroundColor Green
Write-Host "Now run the manual matrix in docs/DESKTOP_UPGRADE_MATRIX.md for real installers." -ForegroundColor Green
Restore-Env

# Start ARTEF for local development on Windows (no Docker): API, two demo agents, website.
# Each service opens in its own PowerShell window; close a window (or press Ctrl+C in it) to stop it.
# Services whose port is already in use are skipped.
#
# Usage (from anywhere):  powershell -ExecutionPolicy Bypass -File C:\path\to\ARTEF\scripts\start_dev.ps1
# Python: uses $env:ARTEF_PYTHON if set, else .venv\Scripts\python.exe in the repo, else ~\.artef-venv.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

$Python = $env:ARTEF_PYTHON
if (-not $Python) {
    foreach ($candidate in @("$Root\.venv\Scripts\python.exe", "$HOME\.artef-venv\Scripts\python.exe")) {
        if (Test-Path $candidate) { $Python = $candidate; break }
    }
}
if (-not $Python -or -not (Test-Path $Python)) {
    Write-Error "Python virtual environment not found. Create it first (see README 'Local development') or set ARTEF_PYTHON."
}
if (-not (Test-Path "$Root\backend\.env")) {
    Write-Error "backend\.env not found. Run: $Python $Root\scripts\dev_setup.py"
}

function Test-PortInUse([int]$Port) {
    [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Start-Service([string]$Name, [int]$Port, [string]$Command) {
    if (Test-PortInUse $Port) {
        Write-Host ("{0,-24} already running on port {1} - skipped" -f $Name, $Port) -ForegroundColor Yellow
        return
    }
    $title = "`$host.UI.RawUI.WindowTitle = 'ARTEF - $Name (port $Port)'; "
    Start-Process powershell -ArgumentList @("-NoExit", "-NoProfile", "-Command", $title + $Command) | Out-Null
    Write-Host ("{0,-24} starting on port {1}" -f $Name, $Port) -ForegroundColor Green
}

# Evaluations run inside the API process (no Redis/Celery worker needed for local use).
Start-Service "Backend API" 8000 "Set-Location '$Root\backend'; `$env:CELERY_TASK_ALWAYS_EAGER='true'; & '$Python' -m uvicorn app.main:app --port 8000"
Start-Service "Demo agent (safe)" 9001 "Set-Location '$Root'; & '$Python' demo\target_agent.py --mode safe --port 9001"
Start-Service "Demo agent (vulnerable)" 9002 "Set-Location '$Root'; & '$Python' demo\target_agent.py --mode vulnerable --port 9002"
Start-Service "Website" 3000 "Set-Location '$Root\frontend'; npx -y pnpm@10.18.0 dev"

Write-Host ""
Write-Host "Waiting for the API..." -NoNewline
for ($i = 0; $i -lt 60; $i++) {
    if (Test-PortInUse 8000) { break }
    Start-Sleep -Seconds 1
    Write-Host "." -NoNewline
}
Write-Host ""
if (Test-PortInUse 8000) {
    Write-Host "Ready. Open http://localhost:3000 and sign in as 'admin' with SEED_ADMIN_PASSWORD from backend\.env" -ForegroundColor Cyan
} else {
    Write-Host "The API did not start. Check the 'ARTEF - Backend API' window for the error." -ForegroundColor Red
}

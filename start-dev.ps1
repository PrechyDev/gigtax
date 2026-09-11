#Requires -Version 5.1
<#
  Starts GigTax locally: Postgres (Docker), backend (FastAPI/uvicorn), frontend (Vite).
  Run from the repo root:  .\start-dev.ps1

  Backend and frontend each open in their own PowerShell window with logs visible -
  close the window or Ctrl+C inside it to stop that one service. Use .\stop-dev.ps1
  to stop everything (including Postgres) in one go.
#>

$root = $PSScriptRoot

function Wait-ForPort {
    param([int]$Port, [int]$TimeoutSeconds = 30)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

Write-Host "==> Starting Postgres (Docker)..." -ForegroundColor Cyan
Push-Location $root
docker compose up -d db
$dockerExit = $LASTEXITCODE
Pop-Location
if ($dockerExit -ne 0) {
    Write-Error "docker compose up -d db failed (exit $dockerExit) - is Docker Desktop running?"
    exit 1
}

Write-Host "==> Waiting for Postgres to accept connections..." -ForegroundColor Cyan
$pgReady = $false
for ($i = 0; $i -lt 30; $i++) {
    docker exec gigtax-postgres pg_isready -U postgres 1>$null
    if ($LASTEXITCODE -eq 0) { $pgReady = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $pgReady) {
    Write-Warning "Postgres did not report ready within 30s - continuing anyway; the backend will fail fast if it's not actually up."
}

Push-Location "$root\backend"
$backendVenv = poetry env info --path
Pop-Location
if (-not $backendVenv) {
    Write-Host "==> Installing backend dependencies (first run)..." -ForegroundColor Cyan
    Push-Location "$root\backend"
    poetry install
    Pop-Location
}

Write-Host "==> Applying database migrations (also re-syncs the category taxonomy)..." -ForegroundColor Cyan
Push-Location "$root\backend"
poetry run alembic upgrade head
$migrateExit = $LASTEXITCODE
Pop-Location
if ($migrateExit -ne 0) {
    Write-Error "alembic upgrade head failed (exit $migrateExit) - check the output above."
    exit 1
}

if (-not (Test-Path "$root\frontend\node_modules")) {
    Write-Host "==> Installing frontend dependencies (first run)..." -ForegroundColor Cyan
    Push-Location "$root\frontend"
    npm install
    Pop-Location
}

Write-Host "==> Starting backend on http://localhost:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root\backend'; poetry run uvicorn main:app --reload --port 8000"
)

Write-Host "==> Waiting for the backend to come up..." -ForegroundColor Cyan
if (-not (Wait-ForPort -Port 8000 -TimeoutSeconds 60)) {
    Write-Warning "Backend didn't report ready within 60s - check its window for errors."
}

Write-Host "==> Starting frontend on http://localhost:5173 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root\frontend'; npm run dev -- --port 5173"
)

Write-Host ""
Write-Host "GigTax is starting up:" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8000/docs"
Write-Host "  Frontend: http://localhost:5173"
Write-Host ""
Write-Host "Each service runs in its own window. Run .\stop-dev.ps1 to stop everything." -ForegroundColor DarkGray

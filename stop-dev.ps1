#Requires -Version 5.1
<#
  Stops GigTax's local dev processes (backend on :8000, frontend on :5173/:5174) and
  the Postgres container. Postgres data is preserved - it lives in a named Docker
  volume, not the container itself, so this is safe to run any time.

  Matches by command line, not just by which PID currently owns the port: uvicorn's
  --reload spawns a reloader process plus a separate worker, and Windows can keep
  reporting the (already-exited) reloader as the port's owner even after only the
  worker is left actually serving - a port-only kill misses it entirely.
#>

function Stop-ProcessesByCommandLine {
    param([string]$Pattern, [string]$Label)
    $matches = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -like $Pattern }
    foreach ($m in $matches) {
        Write-Host "Stopping $Label (PID $($m.ProcessId))..." -ForegroundColor Yellow
        Stop-Process -Id $m.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Stop-ListenerOnPort {
    param([int]$Port)
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $conns) {
        $procId = $conn.OwningProcess
        if (Get-Process -Id $procId -ErrorAction SilentlyContinue) {
            Write-Host "Stopping process on port $Port (PID $procId)..." -ForegroundColor Yellow
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "==> Stopping backend..." -ForegroundColor Cyan
Stop-ProcessesByCommandLine -Pattern "*uvicorn*main:app*" -Label "backend (uvicorn)"
Stop-ListenerOnPort -Port 8000

Write-Host "==> Stopping frontend..." -ForegroundColor Cyan
Stop-ProcessesByCommandLine -Pattern "*vite*" -Label "frontend (vite)"
Stop-ListenerOnPort -Port 5173
Stop-ListenerOnPort -Port 5174

Write-Host "==> Stopping Postgres container..." -ForegroundColor Cyan
Push-Location $PSScriptRoot
docker compose stop db
Pop-Location

Write-Host ""
Write-Host "Done. Postgres data is preserved - run .\start-dev.ps1 to bring everything back up." -ForegroundColor Green

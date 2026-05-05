# SquidSquad — ensure deps are installed, then run the harness.
# Usage: pwsh start.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

# --- Python ---
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Install Python from https://python.org" -ForegroundColor Red; exit 1
}

# --- fastapi + uvicorn ---
python -c "import fastapi; import uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) { pip install fastapi uvicorn }

# --- Go ---
python references/scripts/harness.py @args

# SquidSquad — ensure deps, sync clones, run harness.
# Usage: pwsh start.ps1

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

# --- Python ---
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Install Python from https://python.org" -ForegroundColor Red; exit 1
}

# --- Runtime Python deps (#11613) ---
# Install the FULL runtime set from requirements.txt, not just fastapi+uvicorn —
# watchdog and pyyaml are also imported at runtime. The import probe covers
# every runtime dep so a partial environment triggers a reinstall.
python -c "import fastapi, uvicorn, starlette, watchdog, yaml" 2>$null
if ($LASTEXITCODE -ne 0) { pip install -r requirements.txt }

# --- Sync all clones to main ---
Write-Host "Syncing clones..."
# Primary repo
$null = git checkout main 2>&1
$null = git pull --rebase 2>&1
Write-Host "  primary: OK"

# Agent clones from .local-config
$localConfig = Join-Path $RepoRoot ".squidsquad\.local-config"
if (Test-Path $localConfig) {
    Get-Content $localConfig | ForEach-Object {
        if ($_ -match '^\- \*\*(\w+)\*\*:\s*(.+)') {
            $role = $Matches[1]
            $path = $Matches[2].Trim()
            if ($path -eq ".") { return }
            if (-not [System.IO.Path]::IsPathRooted($path)) {
                $path = Join-Path $RepoRoot $path
            }
            $path = [System.IO.Path]::GetFullPath($path)
            if (Test-Path $path) {
                Push-Location $path
                try {
                    $null = git checkout main 2>&1
                    $null = git pull --rebase 2>&1
                    Write-Host "  ${role}: OK"
                } catch {
                    Write-Host "  ${role}: WARN (could not sync)"
                }
                Pop-Location
            } else {
                Write-Host "  ${role}: MISSING ($path)"
            }
        }
    }
}

# --- Go ---
python references/scripts/harness.py @args

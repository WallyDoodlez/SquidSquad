# SquidSquad — THE single Windows launcher (#13318).
#
# Consolidates the former start.ps1 + start.bat + start-harness.bat +
# restart-harness.bat into one script. Running it brings up ALL of SquidSquad:
#   deps -> clone-sync -> harness (supervised, detached) -> agent fleet -> TUI.
#
# This script lives in .squidsquad/ (NOT repo root). It resolves the project
# repo root as its own parent directory and operates from there.
#
# Usage:
#   pwsh .squidsquad/start.ps1                full bring-up: deps + sync + harness + TUI
#   pwsh .squidsquad/start.ps1 --bare         harness only (no deps/sync/TUI), foreground
#   pwsh .squidsquad/start.ps1 --no-setup     alias for --bare
#   (any other args are passed through to harness.py)
#
# Behaviors folded in:
#   - deps + clone-sync           (former start.ps1)
#   - supervised auto-relaunch    (former restart-harness.bat, #12825 — exit-42
#                                  relaunch / exit-0 stop / crash-loop guard)
#   - bare/no-setup path          (former start-harness.bat, #12525)
#   - TUI bundling                (references/tui/app.py, #12801/#13277)

$ErrorActionPreference = "Continue"

# --- Repo-root resolution (script is in .squidsquad/, repo root is its parent) ---
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# --- Parse flags (everything non-flag is a harness pass-through arg) ---
$Bare = $false
$HarnessArgs = @()
foreach ($a in $args) {
    if ($a -eq "--bare" -or $a -eq "--no-setup") { $Bare = $true }
    else { $HarnessArgs += $a }
}

# --- Supervised-loop knobs (overridable; tests point SQUIDSQUAD_HARNESS_CMD at a stub) ---
$RestartCode    = if ($env:SQUIDSQUAD_HARNESS_RESTART_CODE)    { [int]$env:SQUIDSQUAD_HARNESS_RESTART_CODE }    else { 42 }
$CrashThreshold = if ($env:SQUIDSQUAD_HARNESS_CRASH_THRESHOLD) { [int]$env:SQUIDSQUAD_HARNESS_CRASH_THRESHOLD } else { 3 }
$CrashWindow    = if ($env:SQUIDSQUAD_HARNESS_CRASH_WINDOW)    { [int]$env:SQUIDSQUAD_HARNESS_CRASH_WINDOW }    else { 60 }
$HarnessCmd     = if ($env:SQUIDSQUAD_HARNESS_CMD)             { $env:SQUIDSQUAD_HARNESS_CMD }                  else { "python references/scripts/harness.py" }

# --- Harness port + liveness probe (singleton-safety: never double-start) ---
function Get-HarnessPort {
    $p = 7373
    $pf = Join-Path $RepoRoot ".squidsquad\.harness-port"
    if (Test-Path $pf) {
        $raw = (Get-Content $pf -Raw -ErrorAction SilentlyContinue) -replace '[^0-9]', ''
        if ($raw) { $p = [int]$raw }
    }
    return $p
}
function Test-HarnessUp {
    try {
        $port = Get-HarnessPort
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 "http://127.0.0.1:$port/status" -ErrorAction Stop | Out-Null
        return $true
    } catch { return $false }
}

# --- Supervised harness loop (folds restart-harness.bat #12825) ---
#   42    -> RESTART: relaunch immediately (POST /restart exits with this code).
#   0     -> clean STOP (POST /shutdown / operator Ctrl+C) -> do NOT relaunch.
#   other -> CRASH: relaunch, but a crash-loop guard gives up after
#            CrashThreshold rapid consecutive crashes.
function Invoke-Supervised {
    $crashCount = 0
    # Split HarnessCmd into exe + leading args, then append pass-through args.
    $parts   = $HarnessCmd -split '\s+'
    $exe     = $parts[0]
    $baseArg = @($parts[1..($parts.Count - 1)])
    while ($true) {
        $start = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        & $exe @baseArg @HarnessArgs
        $code = $LASTEXITCODE
        $end = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

        if ($code -eq 0) {
            Write-Host "[start] harness exited cleanly (0) - not relaunching."
            return 0
        }
        if ($code -eq $RestartCode) {
            Write-Host "[start] restart requested (exit $code) - relaunching..."
            $crashCount = 0   # intentional restart — reset crash accounting
            continue
        }
        # Abnormal exit -> crash-loop guard. A run that lasted at least
        # CrashWindow seconds was healthy (not a boot loop), so it forgives
        # prior crashes; the crash that ended it then starts a fresh streak at 1.
        if (($end - $start) -ge $CrashWindow) { $crashCount = 0 }
        $crashCount++
        Write-Host "[start] harness exited abnormally (code $code) - crash $crashCount/$CrashThreshold."
        if ($crashCount -ge $CrashThreshold) {
            Write-Error "[start] crash-loop detected ($crashCount crashes) - giving up. See output above, .squidsquad\harness-supervisor.log (detached full-mode output), and .squidsquad\harness-errors.log."
            return 1
        }
        Start-Sleep -Seconds 1
    }
}

# --- Setup: deps + clone-sync (folds start.ps1; skipped in --bare) ---
function Initialize-Deps {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host "Install Python from https://python.org" -ForegroundColor Red; exit 1
    }
    # Runtime deps (#11613): import probe covers every runtime dep so a partial
    # environment triggers a full reinstall from requirements.txt.
    python -c "import fastapi, uvicorn, starlette, watchdog, yaml" 2>$null
    if ($LASTEXITCODE -ne 0) { pip install -r requirements.txt }
    # TUI dep (#12801/#13318): full mode launches references/tui/app.py, which
    # imports `textual` — kept in requirements-tui.txt, separate from the harness
    # runtime set. Without this, full mode would pass the harness-dep probe then
    # crash at TUI launch on a fresh machine.
    python -c "import textual" 2>$null
    if ($LASTEXITCODE -ne 0) { pip install -r requirements-tui.txt }
}

function Sync-Clones {
    Write-Host "Syncing clones..."
    $null = git checkout main 2>&1
    $null = git pull --no-rebase 2>&1
    Write-Host "  primary: OK"
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
                        $null = git pull --no-rebase 2>&1
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
}

# --- BARE mode (#12525): harness only, no deps/sync/TUI, foreground supervised ---
# Also the path full-mode re-invokes (detached) to own the harness lifecycle, and
# the path #12527's greenfield smoke test uses.
if ($Bare) {
    Write-Host "[start] bare mode (#12525): harness only (no deps/sync/TUI)."
    exit (Invoke-Supervised)
}

# --- FULL mode: deps + sync, then detached supervised harness + foreground TUI ---
Initialize-Deps
Sync-Clones

if (Test-HarnessUp) {
    Write-Host "[start] harness already running on port $(Get-HarnessPort) — attaching TUI (singleton-safe)."
} else {
    Write-Host "[start] launching harness (supervised, detached background)..."
    # Re-invoke self in --bare mode, detached, so the supervised loop (#12825)
    # survives this script exiting AND the TUI quitting (AC4/AC6). Start-Process
    # spawns an independent process that outlives this one.
    $selfPath = Join-Path $ScriptDir "start.ps1"
    $spArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $selfPath, "--bare") + $HarnessArgs
    $log = Join-Path $RepoRoot ".squidsquad\harness-supervisor.log"
    Start-Process -FilePath "pwsh" -ArgumentList $spArgs -WindowStyle Hidden `
        -RedirectStandardOutput $log -RedirectStandardError "$log.err" | Out-Null
    # Wait (<=30s) for the harness to answer /status before launching the TUI.
    for ($i = 0; $i -lt 60; $i++) {
        if (Test-HarnessUp) { break }
        Start-Sleep -Milliseconds 500
    }
    if (-not (Test-HarnessUp)) { Write-Host "[start] WARNING: harness not reachable yet; TUI will keep retrying." }
}

# TUI in foreground (#12801). Quitting it (q / Ctrl-C) leaves the detached
# harness + agent fleet running in the background (AC6); re-running this script
# re-attaches the TUI without double-starting the harness.
python references/tui/app.py --url "http://127.0.0.1:$(Get-HarnessPort)"

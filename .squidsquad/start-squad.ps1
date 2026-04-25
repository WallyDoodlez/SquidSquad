# Start all configured SquidSquad agents.
# Calls boot_remote.py --all which handles liveness detection,
# .stop sentinel checks, clone path resolution, and PID singleton enforcement.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

Write-Host "🦑 Starting SquidSquad agents..."
python references/scripts/boot_remote.py --all

exit $LASTEXITCODE

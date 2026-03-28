$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

$config = Get-Content .squidsquad/config.md -Raw
$v = if ($config -match '(\d+\.\d+[\.\d]*)') { $Matches[1] } else { '?' }

Write-Host ""
Write-Host "    ▗▄▄▄▄▖"
Write-Host "   ▟██████▙"
Write-Host "    ▐▌▀ ▀▐▌"
Write-Host "  ▜██████▛▘"
Write-Host "   ▐██████"
Write-Host "    ▌▌▌▌▌▌"
Write-Host "  S Q U I D S Q U A D   v$v  -  skill"
Write-Host ""

$interval = if ($config -match "Minutes.*?(\d+)") { [int]$Matches[1] } else { 10 }

Write-Host "[squidsquad] skill agent starting. loop interval: ${interval}min"
Write-Host "[squidsquad] press Ctrl+C to stop"
Write-Host ""

$n = 0
while ($true) {
    $n++
    $time = Get-Date -Format "HH:mm:ss"
    Write-Host "[squidsquad] ---- cycle $n started at $time ----"
    claude --dangerously-skip-permissions --verbose -p "Read .squidsquad/skill/CLAUDE.md for your instructions. Begin your Ralph Loop cycle now." 2>&1
    Write-Host ""
    Write-Host "[squidsquad] ---- cycle $n complete. sleeping ${interval}min ----"
    Start-Sleep -Seconds ($interval * 60)
}

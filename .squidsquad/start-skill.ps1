$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

$config = Get-Content .squidsquad/config.md -Raw
$interval = if ($config -match "Minutes.*?(\d+)") { [int]$Matches[1] } else { 10 }

Write-Host "[squidsquad] skill agent starting. loop interval: ${interval}min"
Write-Host "[squadsquad] press Ctrl+C to stop"
Write-Host ""

$n = 0
while ($true) {
    $n++
    $time = Get-Date -Format "HH:mm:ss"
    Write-Host "[squidsquad] ---- cycle $n started at $time ----"
    $prompt = Get-Content .squidsquad/skill/CLAUDE.md -Raw
    claude --permission-mode auto --enable-auto-mode -p $prompt
    Write-Host ""
    Write-Host "[squidsquad] ---- cycle $n complete. sleeping ${interval}min ----"
    Start-Sleep -Seconds ($interval * 60)
}

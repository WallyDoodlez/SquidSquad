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

"skill" | Set-Content .squidsquad/.active-role -NoNewline
claude --permission-mode auto

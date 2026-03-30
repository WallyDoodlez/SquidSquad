[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

$config = Get-Content .squidsquad/config.md -Raw -Encoding UTF8
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

# Write role for statusline (not used for auto-boot — that uses system prompt)
"skill" | Set-Content .squidsquad/.active-role -NoNewline

claude --permission-mode auto --append-system-prompt "SQUIDSQUAD_ROLE=skill" "start the loop"
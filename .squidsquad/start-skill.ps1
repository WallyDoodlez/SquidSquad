[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

$config = Get-Content .squidsquad/config.md -Raw -Encoding UTF8
$v = if ($config -match '(\d+\.\d+[\.\d]*)') { $Matches[1] } else { '?' }

Write-Host ""
Write-Host "      ▗▄▖"
Write-Host "     ▟█ █▙"
Write-Host "    ▐█• •█▌"
Write-Host "   ███████"
Write-Host "   ▐█████▌"
Write-Host "    ▐▌▐▌▐▌"
Write-Host "  S Q U I D S Q U A D   v$v  -  skill"
Write-Host ""

# Inject permissions from template into settings.json
& (Join-Path $repoRoot ".squidsquad/inject-permissions.ps1")

# Write role for statusline (not used for auto-boot -- system prompt handles that)
"skill" | Set-Content .squidsquad/.active-role -NoNewline

# Clear and initialize status bar state
Remove-Item .squidsquad/skill/current-state -ErrorAction SilentlyContinue
"idle|Initializing..." | Set-Content .squidsquad/skill/current-state -NoNewline

claude --enable-auto-mode --append-system-prompt "SQUIDSQUAD_ROLE=skill" "Skill dev - start the loop"

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

# Write role for statusline (not used for auto-boot -- system prompt handles that)
"skill" | Set-Content .squidsquad/.active-role -NoNewline

# Clear and initialize status bar state
Remove-Item .squidsquad/skill/current-state -ErrorAction SilentlyContinue
"idle|Initializing..." | Set-Content .squidsquad/skill/current-state -NoNewline

# Launch heartbeat in background
$hbInterval = if ($config -match 'Heartbeat Interval Seconds.*?(\d+)') { $Matches[1] } else { '10' }
$hbProc = Start-Process -FilePath "bash" -ArgumentList ".squidsquad/heartbeat.sh", "skill", $hbInterval -PassThru -NoNewWindow
try {
    claude --permission-mode auto --append-system-prompt "SQUIDSQUAD_ROLE=skill" "start the loop"
} finally {
    Stop-Process -Id $hbProc.Id -ErrorAction SilentlyContinue
}

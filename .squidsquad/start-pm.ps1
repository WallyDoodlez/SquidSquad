[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

if (Test-Path .squidsquad) {
    $config = Get-Content .squidsquad/config.md -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    $v = if ($config -match '(\d+\.\d+[\.\d]*)') { $Matches[1] } else { '?' }

    Write-Host ""
    Write-Host "      ▗▄▖"
    Write-Host "     ▟█ █▙"
    Write-Host "    ▐█• •█▌"
    Write-Host "   ███████"
    Write-Host "   ▐█████▌"
    Write-Host "    ▐▌▐▌▐▌"
    Write-Host "  S Q U I D S Q U A D   v$v  -  PM / QA"
    Write-Host ""
}

# Write role for statusline (not used for auto-boot -- system prompt handles that)
"pm" | Set-Content .squidsquad/.active-role -NoNewline

# Clear and initialize status bar state
Remove-Item .squidsquad/pm/current-state -ErrorAction SilentlyContinue
"idle|Initializing..." | Set-Content .squidsquad/pm/current-state -NoNewline

claude --enable-auto-mode --append-system-prompt "SQUIDSQUAD_ROLE=pm" "start the loop"

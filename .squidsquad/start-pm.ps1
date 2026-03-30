[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

if (Test-Path .squidsquad) {
    $config = Get-Content .squidsquad/config.md -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    $v = if ($config -match '(\d+\.\d+[\.\d]*)') { $Matches[1] } else { '?' }

    Write-Host ""
    Write-Host "    ▗▄▄▄▄▖"
    Write-Host "   ▟██████▙"
    Write-Host "    ▐▌▀ ▀▐▌"
    Write-Host "  ▜██████▛▘"
    Write-Host "   ▐██████"
    Write-Host "    ▌▌▌▌▌▌"
    Write-Host "  S Q U I D S Q U A D   v$v  -  PM / QA"
    Write-Host ""
}

# Write role for statusline (not used for auto-boot — that uses system prompt)
"pm" | Set-Content .squidsquad/.active-role -NoNewline

claude --permission-mode auto --append-system-prompt "SQUIDSQUAD_ROLE=pm" "start the loop"
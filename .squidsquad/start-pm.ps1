$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

if (Test-Path .squidsquad) {
    $config = Get-Content .squidsquad/config.md -Raw -ErrorAction SilentlyContinue
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

claude --permission-mode auto --append-system-prompt-file .squidsquad/pm/CLAUDE.md

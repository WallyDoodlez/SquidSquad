[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

# Parse --name flag (optional override for agent alias)
$AgentName = ""
for ($i = 0; $i -lt $args.Count; $i++) {
    if ($args[$i] -eq "--name" -and ($i + 1) -lt $args.Count) {
        $AgentName = $args[$i + 1]
        break
    }
}

# Read alias from config if no --name override
if (-not $AgentName) {
    try {
        $AgentName = (python references/scripts/config.py alias skill 2>$null).Trim()
    } catch {
        $AgentName = "squidsquad-skill"
    }
    if (-not $AgentName) { $AgentName = "squidsquad-skill" }
}

$config = Get-Content .squidsquad/config.md -Raw -Encoding UTF8
$v = if ($config -match '(\d+\.\d+[\.\d]*)') { $Matches[1] } else { '?' }

Write-Host ""
Write-Host "      ▗▄▖"
Write-Host "     ▟█ █▙"
Write-Host "    ▐█• •█▌"
Write-Host "   ███████"
Write-Host "   ▐█████▌"
Write-Host "    ▐▌▐▌▐▌"
Write-Host "  S Q U I D S Q U A D   v$v  -  $AgentName"
Write-Host ""

# Inject permissions from template into settings.json
& (Join-Path $repoRoot ".squidsquad/inject-permissions.ps1")

# Write role for statusline (not used for auto-boot -- system prompt handles that)
"skill" | Set-Content .squidsquad/.active-role -NoNewline

# Clear and initialize status bar state
Remove-Item .squidsquad/skill/current-state -ErrorAction SilentlyContinue
"idle|Initializing..." | Set-Content .squidsquad/skill/current-state -NoNewline

claude --dangerously-skip-permissions --session-name "$AgentName" --append-system-prompt "SQUIDSQUAD_ROLE=skill" "Skill dev - start the loop"

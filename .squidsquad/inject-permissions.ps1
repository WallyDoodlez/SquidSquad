# inject-permissions.ps1 — Merge .squidsquad/permissions.template.json into .claude/settings.json
# Called by startup scripts before launching Claude.
#
# Strategy: read the template (stripping comment lines), then replace
# .permissions.allow in settings.json while preserving everything else.

$repoRoot = git rev-parse --show-toplevel
$template = Join-Path $repoRoot ".squidsquad/permissions.template.json"
$settings = Join-Path $repoRoot ".claude/settings.json"

if (-not (Test-Path $template)) {
    Write-Host "[inject-permissions] WARNING: $template not found - skipping."
    return
}

# Ensure settings.json exists
if (-not (Test-Path $settings)) {
    '{}' | Set-Content $settings -Encoding UTF8
}

# Read template, strip BOM if present, strip comment lines (values starting with "//")
$permsRaw = [System.IO.File]::ReadAllText($template, [System.Text.Encoding]::UTF8)
$permsArray = ($permsRaw | ConvertFrom-Json) | Where-Object { -not $_.StartsWith("//") }

# Read existing settings (strip BOM if present) and inject permissions
$settingsRaw = [System.IO.File]::ReadAllText($settings, [System.Text.Encoding]::UTF8)
$settingsObj = $settingsRaw | ConvertFrom-Json

if (-not $settingsObj.permissions) {
    $settingsObj | Add-Member -NotePropertyName "permissions" -NotePropertyValue ([PSCustomObject]@{ allow = @() })
}

$settingsObj.permissions.allow = $permsArray

# Atomic write (UTF8 without BOM so node/Claude can parse it)
$tmp = "$settings.tmp"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$json = $settingsObj | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($tmp, $json, $utf8NoBom)
Move-Item -Path $tmp -Destination $settings -Force

$count = $permsArray.Count
Write-Host "[inject-permissions] Injected $count permission rules from template."

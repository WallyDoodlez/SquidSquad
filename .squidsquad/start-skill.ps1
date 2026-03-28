$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot
$prompt = Get-Content .squidsquad/skill/CLAUDE.md -Raw
claude --permission-mode auto --enable-auto-mode -p $prompt

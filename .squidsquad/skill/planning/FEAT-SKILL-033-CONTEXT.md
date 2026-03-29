# FEAT-SKILL-033 Context — Heartbeat Branches

## Locked Decisions (from human discussion)

1. **Mechanism**: Orphan heartbeat branches (`heartbeat/<role>`) — human approved after evaluating 5 options
2. **No agent involvement**: heartbeat.sh is a standalone shell script launched by boot scripts — agents are completely unaware
3. **Interval**: Configurable in config.md as `Heartbeat Interval Seconds`, default 10 seconds
4. **Setup**: Explicit step in SKILL.md setup flow so user is aware heartbeat branches will be created
5. **Upgrade**: Upgrade steps must populate `Heartbeat Interval Seconds` in existing config.md if missing (default 10s)
6. **Implementation**: `git mktree` + `git commit-tree` + `git push -f` — no checkout, no working tree impact

## Dev Discretion Areas

- Exact placement of setup step within SKILL.md flow
- heartbeat.sh error handling and cleanup on exit
- PowerShell equivalent for Windows boot scripts
- Whether PM Step 7 should fall back to git log --grep if heartbeat branch doesn't exist yet
- statusline.sh health icon logic update details

## Upgrade & Migration Path

- Existing installs upgrading to this version must get `Heartbeat Interval Seconds: 10` added to config.md
- Boot scripts must be regenerated to include heartbeat launch
- heartbeat.sh must be copied from `references/` to `.squidsquad/` during upgrade
- Old health check logic (git log --grep) should be removed from PM template, not left as fallback (clean break)

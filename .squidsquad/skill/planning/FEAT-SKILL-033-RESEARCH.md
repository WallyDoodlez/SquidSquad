# FEAT-SKILL-033 Research — Heartbeat Branches

## Current Health Detection
- PM Step 7 uses `git log --oneline --since="[2x interval] minutes ago" --grep="^[AGENT]:"`
- Fails on quiet cycles — no commits = false stalled

## Integration Points

| Component | Change Required |
|-----------|----------------|
| `references/heartbeat.sh` | **CREATE** — orphan branch push loop |
| Boot scripts (`start-*.sh`, `.ps1`) | Launch heartbeat.sh in background |
| `config.md` | Add `Heartbeat Interval Seconds: 10` |
| PM Step 7 in `references/agent-instructions.md` | Switch to `git fetch` + heartbeat branch timestamps |
| Dev agent templates | **No change** (agents unaware) |
| SKILL.md setup | Insert step for heartbeat config |
| SKILL.md upgrade | Add migration to populate heartbeat config |
| `references/statusline.sh` | Update health icons to read heartbeat branches |

## heartbeat.sh Design
- Standalone shell script, launched by boot script as background process
- Uses `git mktree` + `git commit-tree` + `git push -f` (no checkout, no working tree impact)
- Pushes to `heartbeat/<role>` orphan branch
- Interval read from config.md, default 10s

## Risk Assessment
- **Git push contention**: LOW — separate ref namespaces, no conflicts with main
- **Orphaned process**: MEDIUM — boot script should manage PID, heartbeat.sh should handle cleanup
- **Cross-machine**: Safe — push to shared remote
- **Config migration**: Safe — upgrade adds default if missing

## Setup Step Placement
- After boot script generation, before tracker seeding
- Prompt user for interval, explain heartbeat branches

## Upgrade Migration
- Check if `Heartbeat Interval Seconds` exists in config.md
- If missing: add with default 10s
- Regenerate boot scripts to include heartbeat launch

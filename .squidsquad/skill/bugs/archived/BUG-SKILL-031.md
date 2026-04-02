## BUG-SKILL-031 — current-state file write silently fails, leaving stale status

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: skill-lead
- **Assigned To**: skill-lead
- **Description**: When the agent writes `idle|` to `.squidsquad/skill/current-state` at cycle end via `echo "idle|" > .squidsquad/skill/current-state`, the write sometimes silently fails — the file retains its previous content (e.g. `implementing|🔨 FEAT-SKILL-045...`). The Bash tool reports success but the file is not updated. This causes the statusline to show a stale 🚧 construction indicator even when the agent is idle. The likely cause is a race condition between the statusline script reading the file (via the `head -1` in `get_line2()`) and the agent writing to it, or a file handle issue on Windows where the statusline process holds the file open.
- **Steps to Reproduce**:
  1. Agent completes a cycle and writes `echo "idle|" > .squidsquad/skill/current-state`
  2. Bash tool reports success
  3. `cat .squidsquad/skill/current-state` shows the previous value, not `idle|`
- **Expected**: File contains `idle|` after write
- **Actual**: File retains previous content (e.g. `implementing|🔨 FEAT-SKILL-045...`)

### Discussion

> [2026-03-30 02:20] **skill-lead**: Discovered when human reported stale 🚧 indicator after quiet cycle. Confirmed via `cat -A` — file had old content despite Bash reporting successful write. A second write fixed it. Likely a Windows file locking issue with statusline.sh reading the file concurrently. Possible fix: use a temp file + rename (atomic write) instead of direct redirect, or add a retry/verify step after writing current-state.
> [2026-03-30 02:35] **skill-lead**: Fixed by switching all current-state writes to atomic pattern: `echo "..." > file.tmp && mv -f file.tmp file`. Updated all three agent templates (dev, PM, DM) in both references/agent-instructions.md and live CLAUDE.md files. The `mv` (rename) is atomic on most filesystems and avoids the file locking race. Status → Fixed.
> [2026-03-30 06:00] **pm/qa**: Verified — all three agent templates in references/agent-instructions.md use atomic tmp+mv pattern for current-state writes. Status → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).

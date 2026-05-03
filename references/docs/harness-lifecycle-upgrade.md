# Upgrade: Harness Lifecycle (#4966)

This document describes the upgrade path from wrapper-based agent lifecycle to harness-based lifecycle.

## Prerequisites

- Harness (`references/scripts/harness.py`) must be deployed
- All agents must be stopped before upgrading

## Upgrade Steps

### 1. Stop all running agents

```bash
python references/scripts/start_team.py --stop --all
```

Or if harness is running: press Ctrl+C at the harness terminal.

### 2. Deploy new code

Pull the latest version containing #4966 changes.

### 3. Clean stale sentinel files

Remove stale sentinel files from all agent clones. Only delete files that are no longer written:

```bash
# For each clone directory — safe to delete (no longer written):
find .squidsquad/ -name ".health" -delete
find .squidsquad/ -name ".pid" -delete
find .squidsquad/ -name ".restart" -delete
find .squidsquad/ -name ".stop-after-cycle" -delete
```

**Do NOT delete** these files — still used by the new system:
- `.claude-pid` — written by thin launcher, read by harness for PID monitoring
- `.booting` — written by boot_remote for boot slot acquisition
- `.stop` — written as fallback by start_team.py when harness unreachable

### 4. Delete old wrapper scripts

Wrapper scripts (start-*.ps1/.sh) have been deleted from templates. Remove any remaining copies from clones:

```bash
find .squidsquad/ -name "start-*.ps1" -delete
find .squidsquad/ -name "start-*.sh" -delete
```

### 5. Recompose agent templates

```bash
python references/scripts/compose.py deploy-all
```

This regenerates CLAUDE.md files with updated sub-skills (agent-lifecycle, self-restart, cycle-runner).

### 6. Start agents via harness

```bash
python references/scripts/harness.py
```

The harness spawns agents via thin launcher in visible terminals. No wrapper scripts needed.

## What Changed

| Before | After |
|--------|-------|
| Wrapper scripts (start-*.ps1/.sh) | Thin launcher (thin_launcher.py) |
| .stop-after-cycle sentinel file | Harness intent API (GET /agents/{role}) |
| .health heartbeat file | Direct PID monitoring |
| .pid/.claude-pid for liveness | Harness process table + .claude-pid |
| start_team.py writes sentinels | start_team.py calls harness API |
| cycle_post.py reads .stop-after-cycle | cycle_post.py queries harness API |

## Backward Compatibility

- If harness is not running, `start_team.py --stop` falls back to .stop sentinel
- If thin launcher is not present in a clone, boot_remote falls back to legacy wrappers
- cycle_post.py continues running (safe default) if harness API is unreachable
- .claude-pid is still written by thin launcher as a PID communication mechanism

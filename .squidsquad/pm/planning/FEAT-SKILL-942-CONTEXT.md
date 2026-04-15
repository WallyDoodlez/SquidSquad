# FEAT-SKILL-942 Context — Boot Process Overhaul

## Scope

Unified boot health reporting: boot script wrapper writes `.health` status file, PM reads it. Includes pre-flight checks (#941 merged), context-pressure fix for all agents, post-spawn verification, and stale wizard cleanup.

## Locked Decisions (human decided)

- **Wrapper writes `.health`**: Boot script wrapper owns the `.health` file (booting/alive/restarting/backoff/dead/error). Agent keeps writing `current-state` for cycle-level detail. health_check.py reads `.health` for liveness, `current-state` for phase info. Clean separation.
- **Post-spawn poll**: boot_remote.py waits up to 30s for `.health` to show `alive` after spawning. Catches immediate boot failures (gh auth, wrong branch, missing files).
- **Wrapper watcher stays**: Fix the context-pressure bug by adding disk-write to all agent templates (PM/QA/DM currently never write the file). Wrapper remains the enforcement layer for context-pressure restarts.
- **#941 merged into #942**: Pre-flight checks (gh auth + main branch) are part of this task. Failures write to `.health` with error details and exit without entering the restart loop.
- **Wrapper enforces self-restart rate limit**: Move the 3/hour limit from agent-side (soft) to wrapper-side (hard enforcement).

## Dev Discretion (dev agent can choose)

- `.health` file format (plain text vs JSON) — as long as it's machine-parseable and human-readable
- Exact pre-flight check order in boot scripts
- How to handle `.health` file cleanup on wrapper exit (delete vs write `dead`)

## Side Effect Mitigations (required)

- Re-compose QA and DM CLAUDE.md to fix stale wizard agent references
- health_check.py must gracefully handle missing `.health` file (fall back to mtime for non-upgraded agents)
- boot_remote.py must read `.health` instead of raw PID checks but still work if `.health` doesn't exist yet

## Upgrade Path (required)

- `compose.py boot <role>` for each role to regenerate boot scripts with new `.health` writes
- `compose.py deploy <role>` for QA/DM to fix wizard refs and add context-pressure disk-write
- Graceful degradation: old boot scripts without `.health` support still work — health_check.py falls back to mtime

## Out of Scope

- Log rotation for boot-attempts.log / restart-log.txt (P2, separate task)
- Cross-platform kill consistency (P2, separate task)
- SQLite scan index (#922, separate task)

# FEAT-PM-4966 Context — Harness Absorbs Wrapper: Full Agent Lifecycle Ownership

## Scope

The harness becomes the single owner of agent lifecycle. Wrapper scripts are eliminated. The harness spawns, monitors, restarts, and stops agents directly. All sentinel files except .stop-after-cycle are eliminated. New endpoints for health and config. Ctrl+C escalation for graceful shutdown.

## Locked Decisions (human decided)

- **Spawn model**: Thin launcher + PID report for now. The harness spawns a minimal script via wt.exe that starts claude and writes its PID to a known location. Harness reads the PID after spawn. **Future vision**: harness becomes a console app + web server. The console allows switching to "view" any agent's terminal. A web frontend relays the shells. This is out of scope for this task but informs the architecture — design for future console integration.

- **Crash recovery**: Harness writes `.squidsquad/.harness-state.json` with per-agent PIDs on every spawn/death event. On harness restart, reads the file and checks which PIDs are still alive. One file replaces all per-agent .pid/.claude-pid sentinels.

- **Pre-flight split**: Harness does gh auth check once at startup (not per-spawn). cycle_pre.py handles git pull and branch enforcement per cycle. Clean separation — harness owns auth, cycle_pre owns git state.

- **Shutdown key**: Ctrl+C with escalation. First Ctrl+C = graceful stop (write .stop-after-cycle, wait for cycle end). Second Ctrl+C within 5s = warn about force kill. Third Ctrl+C = force kill process. Cross-platform, works with existing uvicorn signal handling.

- **Wrapper removal**: Wrapper scripts deleted entirely. No respawn loop in wrappers — harness is the wrapper. Template wrappers (references/templates/start-role.*) also deleted.

- **.stop-after-cycle eliminated entirely**: Replaced with harness intent API. cycle_post.py calls `GET /agents/{role}` and reads the `intent` field (endpoint already exists). No sentinel file written or read. Harness sets intent in-memory only. Safe default on API failure = "no intent, continue running." Clone port discovery via parent-directory walk + default port 7373 fallback. See FEAT-PM-4966-SENTINEL-RESEARCH.md for full analysis.

- **.stop file eliminated**: Intent lives in harness memory only. No .stop sentinel written or read.

- **.restart file eliminated**: Harness manages restarts directly via intent state machine.

- **ALL sentinel files eliminated**: .health, .pid, .claude-pid, .stop, .restart, .stop-after-cycle all removed. Zero sentinel files. Intent communicated via harness API only.

## Dev Discretion (dev agent can choose)

- Internal harness data structures for intent state machine (enum, dataclass, dict — dev decides)
- Crash backoff algorithm (exponential, linear, or configurable — dev decides)
- How thin launcher reports PID (file write, stdout, HTTP callback — dev decides, but file is simplest)
- Whether to keep boot_remote.py as a fallback or deprecate entirely
- Whether .harness-state.json includes additional metadata (uptime, crash count, last cycle time)

## Side Effect Mitigations (required)

- **Visible terminal constraint**: Must spawn agents in visible terminal windows (wt.exe/Terminal.app/tmux). Cannot make agents headless. Locked from #4439.
- **Clone isolation**: Each agent runs in a different clone directory. Harness must spawn with correct cwd per agent, read .local-config for paths.
- **Generated script staleness**: Current deployed wrappers are stale vs templates. This task deletes both — no reconciliation needed, just delete.
- **State branch commits**: cycle_post.py commits state after cycle. If harness kills agent mid-cycle, state is not committed. Acceptable — same as current behavior.
- **start_team.py / squidsquad_cli.py overlap**: Both will call harness API after migration. Consolidation opportunity but not required in this task.

## Upgrade Path (required)

1. Stop all running agents (existing wrappers)
2. Deploy new harness with direct spawn capability
3. Clean stale sentinel files across all clones (.health, .pid, .claude-pid, .restart, .stop)
4. Run compose.py deploy-all to regenerate CLAUDE.md files with updated sub-skills
5. Delete all start-{role}.ps1/.sh scripts from clone directories
6. Start agents via harness

## Out of Scope

- Console app with agent view switching (future vision, not this task)
- Web frontend relaying shells (future vision)
- Headless agent mode (future, after console app exists)
- start_team.py / squidsquad_cli.py consolidation (separate task)
- Harness Phase 2 event bus (#4709)

# FEAT-SKILL-050 Research — Urgent cycle trigger

## Summary

SquidSquad agents run on a 30-minute `/loop` interval managed by Claude Code's built-in cron system (`CronCreate`). Between cycles, the agent session is idle — it has handed control back to the `/loop` scheduler and is simply waiting for the next cron fire. There is currently no mechanism for one agent (or the human) to interrupt this wait and force an immediate cycle on another agent. This feature proposes adding an urgent trigger capability so that, for example, when QA finds a broken implementation, the PM can force the skill agent to start working immediately rather than waiting up to 30 minutes.

The fundamental challenge is that Claude Code's `CronCreate` only works within the same Claude session. Agent A cannot call `CronCreate` inside Agent B's session. Agents run in separate clones on the same machine, and the only cross-clone link is `.squidsquad/.local-config` which maps role names to filesystem paths. Writing a file to another agent's clone is possible (FEAT-047 proved this with health checks), but writing a file does not wake up a sleeping cron — the target agent will only see the file when its next scheduled cycle fires.

This means the feature has two distinct sub-problems: (1) a signaling protocol (trigger file format, where it lives, who writes it, what happens when the target reads it), and (2) an actual wake-up mechanism that causes the target to start a cycle sooner than its scheduled interval. Sub-problem 1 is straightforward. Sub-problem 2 is the hard design question with no clean solution in the current architecture.

## Impact Analysis

- **Files touched**:
  - `references/agent-instructions.md` — dev agent template: add trigger file check to Step 1, possibly add a polling sub-step or modified `/loop` invocation
  - `.squidsquad/templates/pm-agent.md` (or `.squidsquad/pm/CLAUDE.md`) — PM template: add ability to write trigger files to other agents, add "tell dev to work now" handling in Step 2
  - `.squidsquad/templates/dm-agent.md` — DM template: same trigger file check at cycle start
  - `SKILL.md` — document the trigger mechanism in the Architecture section and Setup Instructions
  - `.squidsquad/config.md` — possibly a new config value for trigger polling interval
  - `.squidsquad/start-*.ps1` / `.squidsquad/start-*.sh` — boot scripts may need modification if the wake-up mechanism involves an external watcher process
  - All live agent `CLAUDE.md` files — re-generated from templates during upgrade

- **Behavior changes**:
  - Agents gain the ability to write trigger files to other agents' clones via `.local-config` paths
  - Agents gain a new step (or sub-step of Step 1) to check for and consume trigger files
  - PM gains a new human-interaction pattern: "tell [role] to work on X now"
  - The `/loop` invocation or cron setup may change depending on the wake-up mechanism chosen

- **Dependencies**:
  - FEAT-047 (`.local-config` cross-clone paths) — already shipped, provides the filesystem bridge
  - `/loop` skill — understanding its internals is critical; it wraps `CronCreate`
  - Claude Code's cron system — the constraints of `CronCreate`/`CronDelete` define what is possible

## Side Effects

- **Risk 1**: Git conflicts from trigger files — if a trigger file is committed and pushed, both clones may conflict on it. — Severity: M — Mitigation: Trigger files should be `.gitignore`d. They are local-only signals written directly to the target clone's filesystem, never committed.

- **Risk 2**: Windows file locking — writing to another clone's directory while that clone's agent is running could hit file locking issues, especially if the target agent is mid-cycle reading files in `.squidsquad/`. — Severity: M — Mitigation: Use the same atomic write pattern already established (write to `.tmp` then `mv`). Trigger files are small (a few lines of text) and the read is non-blocking.

- **Risk 3**: Stale trigger files — if the target agent is stalled or crashed, the trigger file sits indefinitely. The triggering agent has no feedback that the cycle actually started. — Severity: L — Mitigation: Include a timestamp in the trigger file. Target agent can ignore triggers older than 2x the iteration interval. PM health check (Step 7) already detects stalled agents.

- **Risk 4**: Rapid re-triggering — if PM triggers skill, skill runs a cycle, PM is unhappy with the result and triggers again immediately, this could create a tight loop consuming context rapidly. — Severity: M — Mitigation: Add a cooldown — ignore triggers if the last cycle completed less than N minutes ago (e.g., 2 minutes). Or: consume the trigger file at cycle start so it cannot re-fire.

- **Risk 5**: Polling loop increases baseline resource usage — if agents poll for trigger files between cycles, this adds CPU/disk I/O even when no triggers exist. — Severity: L — Mitigation: Poll infrequently (every 60 seconds). Reading a single small file is negligible overhead.

## Edge Cases

- **Trigger fires during active cycle**: The target agent is already mid-cycle when a trigger file appears. The trigger should be consumed at the START of the next cycle (Step 1). Since the agent is already working, the trigger effectively becomes a no-op for timing (the agent is already active) but should still be read for the reason/priority hint it contains. The agent should check for trigger files after completing its current cycle and before entering the idle wait.

- **Multiple triggers queued**: Two agents (PM and DM) both write trigger files for the skill agent. The trigger file should be append-only or use a directory of trigger files (one per triggering agent). At cycle start, the target reads all triggers, merges the reasons, and clears them. Using a directory (`trigger.d/`) avoids write conflicts.

- **Trigger for agent that is stalled/crashed**: The trigger file is written but the target session is dead. The file sits until the human restarts the agent. On restart, the agent's boot sequence should check for and consume any pending trigger files. The PM's health check (Step 7) already flags stalled agents — the human is the fallback.

- **Self-trigger**: An agent triggers itself. This is valid (e.g., skill agent discovers it needs to re-run after a context pressure exit). The agent writes to its own trigger file. Since it is in the same clone, no cross-clone path needed.

- **Trigger during git pull/rebase**: If a trigger file is committed (it should not be), it could cause merge conflicts. Keeping trigger files in `.gitignore` eliminates this entirely.

- **Human triggers directly**: The human could manually create the trigger file (`echo "reason" > .squidsquad/skill/trigger`) without going through PM. This should work — the mechanism is file-based, not agent-based.

- **Target clone path is wrong or inaccessible**: `.local-config` has a stale path. The triggering agent should catch the write failure, log a warning, and continue. This is not a fatal error.

## Integration Risks

- **Context pressure exits**: If an agent exits due to context pressure (Step 1b), it commits, pushes, and exits. The boot script restarts it. If a trigger file was written just before the exit, the restarted session will see it on its first cycle — this works correctly. However, if the trigger itself causes rapid context consumption (frequent triggers = many cycles = fast context growth), it could accelerate context pressure exits. The cooldown mitigation addresses this.

- **Working state**: If an agent is mid-feature (working-state.md has `in-progress`) and receives a trigger with a specific priority (e.g., "fix BUG-SKILL-035 urgently"), there is a conflict: should the agent abandon its current work to handle the trigger's priority, or finish its current task first? Recommendation: the trigger should NOT override working state. The agent resumes its in-progress task as normal (Step 1c). The trigger's reason is informational — it means "start a cycle now" not "drop everything." If priority override is needed, the PM should update the tracker item's priority field, which the agent's normal triage logic respects.

- **PR flow**: If PR flow is enabled and the agent is on a feature branch, a triggered cycle should still follow normal PR flow. No special handling needed.

- **Interval sync (Step 1d)**: If the trigger mechanism involves creating a one-shot cron, this could conflict with the interval sync logic which expects exactly one cron job. The interval sync step would need to be aware of trigger-related cron entries and not delete them (or: not use cron at all for triggers).

- **Health check (Step 7)**: The PM reads `current-state` mtime from other clones to detect stalled agents. Trigger files add a new signal: if a trigger file exists AND the agent's `current-state` is stale, the PM knows the trigger was not consumed — the agent is definitely stalled, not just idle.

## Upgrade & Migration

- **New config values**: Optionally `Trigger Polling Interval: 60` (seconds) if the polling approach is chosen. Could also be hardcoded initially and made configurable later.

- **New files**:
  - `.squidsquad/<role>/trigger` (or `.squidsquad/<role>/trigger.d/`) — runtime signal files, not committed
  - `.gitignore` addition: `**/trigger` and/or `**/trigger.d/`

- **Template changes**:
  - `references/agent-instructions.md` — dev agent template: new step for trigger check + consumption
  - PM template: new capability to write triggers to other agents
  - DM template: new step for trigger check (same as dev)
  - All three templates: if polling is used, modified `/loop` invocation or new polling sub-loop instruction

- **Upgrade steps**:
  - Run `squidsquad-upgrade` which regenerates templates from `references/agent-instructions.md`
  - Update `.gitignore` if trigger files are used
  - No schema migration needed — no new tracker fields

- **Graceful degradation**: If a user does not upgrade, the trigger file mechanism simply does not exist. Agents continue on their normal cron interval. No existing behavior breaks. Upgraded agents that write trigger files to non-upgraded agents' clones will see the files ignored (the target agent does not check for them). This is harmless — the trigger just has no effect.

## Open Questions

- **Q1**: How does the trigger actually wake the target agent? — **Why**: This is the core unsolved problem. `/loop` uses `CronCreate` which schedules the next invocation on a fixed interval. Between invocations, the Claude Code session is idle — there is no code running that could poll for a file. The realistic options are:

  1. **Reduce `/loop` interval + check trigger at cycle start**: Set `/loop` to a short interval (e.g., 2 minutes) but have the agent skip the full cycle if no trigger file exists AND the last full cycle was recent (within the configured 30-minute interval). This makes every agent poll frequently but only do real work on schedule or when triggered. **Downside**: high cron overhead, many no-op invocations consuming minimal but nonzero context, `/loop` was not designed for this pattern.

  2. **External watcher process**: The boot script (`start-*.ps1`) launches a lightweight file watcher (PowerShell `FileSystemWatcher` or `inotifywait` on Linux) alongside the Claude session. When the watcher detects a trigger file, it runs `claude --send "urgent trigger received — start a cycle now"` (if such a CLI command exists) or creates a one-shot cron. **Downside**: requires understanding Claude Code's CLI for injecting messages into a running session, which may not be supported.

  3. **Accept latency — poll on existing interval**: Write the trigger file, accept that the target agent picks it up on its next scheduled cycle (up to 30 minutes). This is the simplest approach but does not meet the "within seconds" acceptance criterion. It could be combined with a shorter default interval (e.g., 10 minutes) to reduce worst-case latency.

  4. **Dual-cron approach**: Each agent runs TWO cron jobs — one at the normal interval for full cycles, and one at a short interval (e.g., 1-2 minutes) that ONLY checks for trigger files and runs a cycle if one exists. The short-interval cron runs a minimal prompt: "check for trigger file, if present run a full cycle, otherwise exit immediately." **Downside**: each short-interval fire costs a small amount of context; over hours this adds up. Also, `CronCreate` might not support two simultaneous crons cleanly.

  5. **`RemoteTrigger` tool**: The deferred tool list includes a `RemoteTrigger` tool. If this tool allows one Claude session to trigger execution in another session, it could be the native solution. This needs investigation — it may be exactly what is needed, or it may be for something else entirely.

- **Q2**: Should the trigger carry priority information or just a reason string? — **Why**: If the trigger says "fix BUG-SKILL-035 urgently," should the agent reprioritize its backlog? Current triage logic uses the Priority field in the tracker. Mixing priority signals from two sources (tracker field vs. trigger file) adds complexity. Recommendation: trigger carries a reason string only; priority changes go through the tracker.

- **Q3**: Should trigger files use a single file or a directory of files? — **Why**: If multiple agents trigger simultaneously, a single file gets overwritten. A `trigger.d/` directory with one file per trigger avoids this. But a directory adds complexity (cleanup, listing). A single file with append semantics and a lock could also work but is more fragile on Windows.

- **Q4**: What is the `RemoteTrigger` tool in the deferred tools list? — **Why**: If Claude Code natively supports triggering actions in another session, the entire file-based approach may be unnecessary. This tool should be investigated before committing to a design.

## Recommendation

**Needs rethinking.** The signaling protocol (trigger file format, cross-clone write via `.local-config`) is straightforward and low-risk. However, the core acceptance criterion — "target agent starts a new cycle within seconds" — cannot be met with the current architecture without either: (a) a short-interval polling cron that wastes context on no-op invocations, or (b) an external watcher process that depends on undocumented Claude Code CLI capabilities for injecting messages into running sessions.

**Recommended next step**: Investigate the `RemoteTrigger` deferred tool. If it provides cross-session triggering, the design becomes simple: triggering agent calls `RemoteTrigger` targeting the other session, which starts a cycle. If `RemoteTrigger` is not applicable, the most pragmatic approach is Option 4 (dual-cron with a short-interval trigger-check cron), accepting the minor context cost, and documenting the trade-off. Option 3 (accept latency) is the fallback if context cost is deemed too high — it meets all criteria except "within seconds."

# FEAT-SKILL-918 Context — Self-Restart Mechanism (Wire Up Poll Loop)

## Scope

Add a background poller to boot scripts (`.sh` and `.ps1`) that watches for `.squidsquad/{role}/.restart` every 5 seconds while Claude is running. When detected, kill the Claude process. Existing sentinel handling in the restart loop takes over from there.

The sub-skill (`references/sub-skills/common/self-restart.md`) and sentinel detection after exit (lines 123-134 in start-pm.sh) already exist. This task only adds the missing poll loop.

## Locked Decisions (human decided)

- **Background poller at 5s interval**: Spawns a background watcher alongside Claude. Polls `.restart` every 5 seconds.
- **End-of-cycle only**: Agents must only write `.restart` at cycle end (Step 10). Sub-skill already enforces this.
- **Common sub-skill**: `self-restart.md` is already a common sub-skill — no changes needed there.
- **Kill mechanism**: `kill $CHILD_PID` on Unix, `Stop-Process` on Windows.

## Dev Discretion (dev agent can choose)

- How to spawn the background watcher (subshell, co-process, etc.)
- Whether to use SIGTERM or SIGINT for the kill signal
- How to clean up the watcher when Claude exits normally (trap or process group)
- Whether the .ps1 script uses a background job or a timer

## Side Effect Mitigations (required)

- Background watcher MUST be killed when Claude exits normally (cleanup trap)
- Watcher must not interfere with the double Ctrl+C handler
- Watcher must not create zombie processes
- If .restart is stale (left from a crash), boot script already deletes it at line 126 — no change needed

## Upgrade Path (required)

- Existing boot scripts need regeneration: `python references/scripts/compose.py boot [role]`
- Agents running old boot scripts will not have the poll loop — self-restart writes .restart but it won't be detected until the next manual restart. Graceful degradation.
- compose.py boot template must be updated

## Out of Scope

- Changes to self-restart.md sub-skill (already correct)
- Template change detection logic (future follow-up)
- Rate limiting in the shell script (already has max restart counter)

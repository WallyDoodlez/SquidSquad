# FEAT-SKILL-942 Research — Boot Process Audit

## Summary

The SquidSquad boot process is a multi-layered system spanning shell scripts, Python orchestration, and agent CLAUDE.md instructions. After PR #924, the core PID-based boot detection is sound in principle, but **the system has six categories of real problems**: (1) a critical health-detection split-brain where `boot_remote.py` uses PID files but `health_check.py` uses `current-state` mtime — neither consults the other, so they can disagree on whether an agent is alive; (2) the PM agent's CLAUDE.md lacks a `context-pressure` sub-skill entirely, meaning PM never writes the `context-pressure` file that the boot script watcher depends on; (3) stale agent lists baked into QA and DM CLAUDE.md files reference a "wizard" agent that was removed from `config.md`; (4) Windows PID tracking records the PowerShell wrapper PID, not the Claude child process PID, meaning the PID file tracks the wrong process; (5) context pressure writes are not atomic on Windows despite the CLAUDE.md instructions suggesting `mv -f` which is not atomic on NTFS; and (6) there is no `gh auth` or branch verification in the boot scripts, so agents can boot and immediately crash when `tracker.py check-gh` fails.

The boot chain works in the happy path but is fragile at every handoff point. The most impactful fix would be introducing a unified health status file that both the boot script and health check script read/write, eliminating the dual-signal problem. Issue #941 (gh auth + branch checks in boot scripts) and #942 (health status files) should be tackled together — they address the same root cause: boot scripts are fire-and-forget with no pre-flight validation and no post-boot health feedback loop.

## Boot Lifecycle Map

```
1. PM decides to boot (Step "Boot Remote Agents" in Ralph Loop)
   |
   v
2. PM runs: python references/scripts/boot_remote.py --all --json
   |
   +--> boot_remote.py reads .squidsquad/.local-config for clone paths
   +--> boot_remote.py reads .squidsquad/config.md for Dev Agents list
   +--> For each role: reads <clone>/.squidsquad/<role>/.pid
   +--> Checks if PID process is alive (tasklist on Windows, kill -0 on Linux)
   +--> Checks for .stop sentinel
   +--> Checks cooldown (boot-attempts.log, 10 min per role)
   +--> Acquires boot-lock (file lock with 30s TTL)
   |
   v
3. boot_remote.py finds boot script: <clone>/.squidsquad/start-<role>.[ps1|sh]
   |
   v
4. boot_remote.py spawns new terminal:
   - Windows: wt.exe new-tab → pwsh -NoExit -File start-role.ps1
   - macOS: osascript → Terminal.app → bash start-role.sh
   - Linux: tmux new-session → bash start-role.sh
   |
   v
5. Boot script (start-role.ps1 / start-role.sh) runs:
   a. cd to repo root (git rev-parse --show-toplevel)
   b. Read agent alias from config.py
   c. Print squid logo
   d. Run inject-permissions.ps1/sh (inject Claude settings)
   e. Run config.py sync-agents
   f. Set SQUIDSQUAD_ROLE env var
   g. PID lock: check existing .pid file, abort if alive, else write own PID
   h. Enter auto-restart while loop
   |
   v
6. Boot script starts Claude:
   - PS1: Start-Process cmd.exe /c claude --dangerously-skip-permissions ...
   - sh: claude ... &  (backgrounded, CHILD_PID=$!)
   |
   v
7. Boot script starts background watcher (polls every 5s):
   - Checks .restart sentinel → kills Claude if found
   - Checks context-pressure file → if >= threshold, waits for idle|, then kills
   |
   v
8. Claude launches, reads CLAUDE.md via SQUIDSQUAD_ROLE= system prompt line:
   a. CLAUDE.md auto-boot reads .squidsquad/<role>/CLAUDE.md
   b. Startup Permission Check: python references/scripts/tracker.py check-gh
   c. If gh fails → agent exits (Claude exits)
   d. Step 1c: Read working-state.md, resume if active task
   e. Invoke /loop 30m → begins cycling
   |
   v
9. Agent cycles (Ralph Loop):
   - Writes current-state each step (for health_check.py)
   - Writes context-pressure each cycle (for boot script watcher) [SKILL ONLY]
   - Writes idle| at cycle end
   |
   v
10. Health detection (two independent systems):
    A. health_check.py: reads current-state mtime, 2x interval = stalled
    B. boot_remote.py: reads .pid file, checks process alive via OS
    (These never consult each other)
```

**Key handoff gaps:**
- Between step 4 and step 5: boot_remote.py has no confirmation the terminal actually launched Claude
- Between step 5g and step 6: PID file is written for the WRAPPER process, not Claude
- Between step 6 and step 8: Claude may fail to boot (no CLAUDE.md, gh auth fails) — boot script has no visibility
- Between step 9 and step 10: health_check.py and boot_remote.py use different signals

## Impact Analysis

- **Files touched** (boot-related):
  - `.squidsquad/start-<role>.ps1` — Windows boot wrapper (per-role generated)
  - `.squidsquad/start-<role>.sh` — Linux/Mac boot wrapper (per-role generated)
  - `references/templates/start-role.ps1` — Template for PS1 generation
  - `references/templates/start-role.sh` — Template for sh generation
  - `references/scripts/boot_remote.py` — PM's boot orchestration
  - `references/scripts/health_check.py` — Health detection (mtime-based)
  - `.squidsquad/<role>/.pid` — PID lock file
  - `.squidsquad/<role>/.stop` — Stop sentinel
  - `.squidsquad/<role>/.restart` — Self-restart sentinel
  - `.squidsquad/<role>/context-pressure` — Pressure percentage file
  - `.squidsquad/<role>/current-state` — Status bar / health state
  - `.squidsquad/<role>/restart-log.txt` — Restart history
  - `.squidsquad/<role>/working-state.md` — Resume state
  - `.squidsquad/boot-attempts.log` — Boot cooldown tracking
  - `.squidsquad/boot-lock` — Cross-process boot lock
  - `.squidsquad/.local-config` — Clone path mapping
  - `.squidsquad/config.md` — Agent list, intervals, thresholds
  - `.squidsquad/<role>/CLAUDE.md` — Agent instructions (startup sequence)

- **Behavior changes #942 would introduce**: Boot scripts write a structured health status file (e.g., `.squidsquad/<role>/.health`) that both `boot_remote.py` and `health_check.py` read. This replaces the split-brain dual-signal approach.

- **Dependencies**:
  - `boot_remote.py` depends on: `.local-config`, `config.md`, `.pid` files, boot scripts
  - `health_check.py` depends on: `.local-config`, `config.md`, `current-state` mtime
  - Boot scripts depend on: `config.py`, `inject-permissions`, `claude` CLI, `gh` CLI
  - Agent CLAUDE.md depends on: `tracker.py check-gh`, `config.py`, `/loop` command
  - Context pressure watcher depends on: agent writing `context-pressure` file + `current-state` idle

## Contradictions Found

### Contradiction 1: Dual Health Detection — PID vs mtime

**boot_remote.py** determines agent liveness by reading `.squidsquad/<role>/.pid` and checking if that process is alive via OS calls (tasklist on Windows, kill -0 on Unix).

**health_check.py** determines agent health by reading `.squidsquad/<role>/current-state` mtime and comparing against 2x the iteration interval.

**Problem**: These two systems never consult each other and can produce contradictory results:
- Agent crashes mid-cycle but boot script wrapper restarts immediately → PID file exists with live process (wrapper), but `current-state` mtime goes stale → `health_check.py` says STALLED, `boot_remote.py` says ALIVE
- Agent runs normally but is in a long operation → PID alive (correct), mtime recent (correct) — agrees
- Boot script wrapper is in exponential backoff sleep → PID alive (wrapper sleeping), `current-state` says `waiting|Restart backoff` — `health_check.py` may or may not flag as stalled depending on timing
- Claude exits but wrapper is sleeping before restart → PID alive (wrapper), `current-state` stale → ALIVE to boot_remote, STALLED to health_check

### Contradiction 2: PID Tracks Wrong Process on Windows

The PS1 boot script writes `$PID | Set-Content $PidFile` (line 76). `$PID` in PowerShell is the **current process ID** — the PowerShell wrapper process, not the Claude child. Claude is launched via `Start-Process cmd.exe /c claude ...` which creates a separate process tree.

**Result**: `boot_remote.py` checks if the PowerShell wrapper is alive, not if Claude is alive. If Claude crashes but the wrapper is in its restart loop (sleeping), `boot_remote.py` sees a live PID and skips booting. This is by design (the wrapper handles restarts), but:
- If the wrapper hangs or gets stuck, there is no detection
- `health_check.py` uses `current-state` mtime which correctly reflects Claude's actual activity — creating the split-brain from Contradiction 1

On Linux/Mac, `$$` is the shell script PID (also the wrapper), but the sh script has `trap cleanup EXIT` which removes the PID file on exit. The PS1 script uses `try/finally` for the same purpose — both correct for wrapper lifecycle.

### Contradiction 3: PM Missing context-pressure Sub-Skill

The skill agent CLAUDE.md has an explicit `context-pressure` sub-skill (lines 278-304) that instructs the agent to write context pressure to disk:
```bash
echo "[PERCENTAGE]" > .squidsquad/skill/context-pressure.tmp && mv -f ...
```

The PM agent CLAUDE.md Step 1b mentions context pressure checking but **does not include the `context-pressure` sub-skill** and **does not instruct PM to write the pressure to the context-pressure file**. Grep of PM's CLAUDE.md for "context-pressure" returns zero matches.

**Result**: The boot script watcher for PM polls `.squidsquad/pm/context-pressure` every 5 seconds but PM never writes it. PM's context pressure restart path is dead code — PM can only restart via the `.restart` sentinel (self-restart) or crash.

QA and DM CLAUDE.md also lack the `context-pressure` disk-write instruction (checked: they mention "Check context_window.used_percentage" but never write it to disk).

### Contradiction 4: Stale Agent Lists in QA and DM CLAUDE.md

QA CLAUDE.md line 16: `The active dev agents on this project are: **qa, skill, wizard**`
DM CLAUDE.md line 16: `The active dev agents on this project are: **qa, skill, wizard**`
PM CLAUDE.md line 17: `The active dev agents on this project are: **skill**`
config.md line 9: `**Dev Agents**: qa, skill`

**Result**: QA and DM still reference "wizard" which was removed (per commit b222e4e "fix: remove wizard agent"). PM correctly shows only "skill". This is a compose.py deploy issue — QA and DM were not recomposed after the wizard removal.

### Contradiction 5: Boot Script Has No Pre-Flight Checks

The boot script (`start-role.ps1/sh`) does NOT verify:
- `gh auth status` (gh CLI authenticated)
- Current git branch is `main`
- No uncommitted conflicts
- Python is available
- `references/scripts/config.py` exists

Instead, the CLAUDE.md agent instructions say to run `tracker.py check-gh` as the first step after launch. If this fails, the agent exits the conversation, which causes Claude to exit, which the boot script sees as a crash and restarts with exponential backoff.

**Result**: If `gh auth` is broken, the agent enters an infinite crash-restart loop:
1. Boot script starts Claude
2. Claude reads CLAUDE.md, runs `tracker.py check-gh` → fails
3. Agent exits conversation
4. Boot script detects exit after < 120s → "fast crash" → backoff 2s, 4s, 8s, ...
5. Eventually hits 300s max backoff, keeps retrying up to 50 times
6. After 50 restarts, gives up with "Max restarts reached"

This burns through 50 Claude sessions before stopping. Issue #941 proposes adding these checks.

### Contradiction 6: Self-Restart Rate Limit Mismatch

CLAUDE.md self-restart safety rules say: "Maximum 3 self-restarts per hour (tracked in `.squidsquad/[ROLE]/restart-log.txt`). If exceeded, skip the restart."

The boot script wrapper has `$MaxRestarts = 50` with no hourly rate limit — it tracks total consecutive crash restarts but does not distinguish self-restart from crash-restart in its counter. Self-restarts reset `$RestartCount = 0`.

**Result**: The CLAUDE.md 3/hour limit is enforced by the agent (inside Claude), but the boot script wrapper has no such limit. If the agent writes `.restart` sentinel, the wrapper always honors it regardless of frequency. The 3/hour limit only works if the agent correctly reads and counts entries in `restart-log.txt` — which is a soft enforcement (agent instruction, not hard enforcement in the wrapper).

## Side Effects

- **Risk 1**: PM never triggers context-pressure restart — Severity: **M** — Mitigation: Add `context-pressure` sub-skill to PM, QA, and DM CLAUDE.md templates (same as skill has)
- **Risk 2**: gh auth failure causes 50-restart burn loop — Severity: **H** — Mitigation: Add `gh auth status` check to boot script before launching Claude (Issue #941)
- **Risk 3**: Health check and boot detection disagree — Severity: **H** — Mitigation: Introduce a unified `.health` file written by the boot script wrapper (agent alive/dead/restarting/backoff) that health_check.py reads alongside mtime
- **Risk 4**: QA/DM CLAUDE.md reference non-existent wizard agent — Severity: **L** — Mitigation: Re-run `python references/scripts/compose.py deploy qa` and `deploy dm`
- **Risk 5**: Windows PID reuse after reboot — Severity: **L** — Mitigation: The boot script already checks if PID is alive before writing; stale PIDs from dead processes are cleaned. PID reuse could cause a false "already running" if a different process happens to get the old PID, but this is unlikely in practice and self-corrects on next boot attempt.
- **Risk 6**: boot-attempts.log grows unbounded — Severity: **L** — Mitigation: Add log rotation (keep last 100 entries)
- **Risk 7**: Lock file TTL race — `boot_remote.py` uses a 30s TTL on `boot-lock`, but if the system clock is wrong or the spawning takes longer than 30s, a second boot process could steal the lock — Severity: **L** — Mitigation: Acceptable for now; 30s is generous for a spawn operation

## Edge Cases

- **Agent exits in < 2 minutes repeatedly**: Boot script enters exponential backoff (2s, 4s, 8s, ... up to 300s). After 50 total restarts, stops permanently. The `current-state` shows `waiting|Restart backoff` or `error|Max restarts reached`. health_check.py would report STALLED. boot_remote.py would see the wrapper PID as alive and skip booting. **Net result**: Dead agent that both systems handle differently.

- **Two PM instances try to boot the same agent**: `boot-lock` file prevents concurrent spawning (30s TTL). If PM crashes while holding the lock, the lock auto-expires. This is adequately handled.

- **Agent crashes before writing idle| to current-state**: Context pressure watcher polls for `idle|` with a 10-minute timeout, then force-kills. If the agent crashes first, the watcher detects the process exit and breaks its loop. The wrapper then handles the restart. This path works correctly.

- **`.restart` sentinel written but watcher already killed Claude**: The wrapper checks for `.restart` after `WaitForExit()`. If the watcher killed Claude (for context pressure), the sentinel check happens after. If both `.restart` and pressure file exist, `.restart` wins (checked first). This is correct.

- **Boot script killed mid-write of PID file**: PS1 uses `Set-Content` (atomic on Windows). sh uses `echo $$ > file` (not atomic but PID files are small enough that partial writes are extremely unlikely). The `finally` block / EXIT trap ensures cleanup.

- **Agent writes context-pressure, then boot script restarts, but working-state was not saved**: The context-pressure watcher waits for `idle|` state before killing, meaning the cycle should be complete. But the CLAUDE.md says to checkpoint working state in Step 1b and continue the cycle. The actual restart happens at cycle end (self-restart). If the watcher kills Claude before the self-restart step, working state may not be fully saved. **Mitigation**: The watcher's 10-minute wait + idle check should prevent this, but a race exists if the agent writes idle| between steps (e.g., at the very end before the self-restart write).

- **Clone path in .local-config doesn't exist**: boot_remote.py falls back to REPO_ROOT. health_check.py reports "clone path does not exist" as UNKNOWN. The agent would boot in the wrong location. **Should be validated at boot time.**

- **Multiple agents in same clone (no .local-config)**: boot_remote.py uses REPO_ROOT for all agents. PID files would be at `.squidsquad/<role>/.pid` in the same repo. This works for single-clone setups but health_check.py requires .local-config to know about agents at all — without it, no agents are checked.

## Integration Risks

- **boot_remote.py + health_check.py**: These two scripts have no shared state. If #942 introduces a health status file, both scripts need to be updated simultaneously. Partial migration (one reads the new file, the other doesn't) would worsen the split-brain.

- **compose.py + agent CLAUDE.md**: The agent list in CLAUDE.md is baked at compose-deploy time. If agents are added/removed from config.md without re-running compose, the CLAUDE.md instructions become stale (as seen with the wizard agent). The boot process itself is unaffected (boot_remote.py reads config.md dynamically), but agent behavior is affected.

- **Boot script + `/loop` command**: The boot script wrapper handles crash-restart and context-pressure restart. The `/loop` command (inside Claude) handles cycle timing. If Claude is killed by the watcher during a `/loop` sleep (between cycles), this is clean — the wrapper restarts and `/loop` re-initializes. No conflict.

- **Self-restart + boot_remote.py cooldown**: If an agent self-restarts, the wrapper handles it immediately (no cooldown). But boot_remote.py has a 10-minute cooldown per role. If the wrapper fails during self-restart AND boot_remote.py tries to boot the agent, the cooldown might prevent it. The wrapper PID is still alive during self-restart, so boot_remote.py would skip it anyway. No actual conflict in practice.

## Upgrade & Migration

- **New config values**: none (if #942 only changes boot scripts and health check)
- **New files**: `.squidsquad/<role>/.health` (proposed — structured health status file)
- **Template changes**: `references/templates/start-role.ps1` and `start-role.sh` would need updating; all deployed `start-<role>` scripts would need recomposing
- **Upgrade steps**: `compose.py boot <role>` for each role to regenerate boot scripts; `compose.py deploy <role>` for each role to update CLAUDE.md if context-pressure sub-skill is added
- **Graceful degradation**: If user doesn't upgrade boot scripts, old PID-only detection continues working. health_check.py would need to handle missing `.health` file gracefully (fall back to mtime check).

## Capability Gaps

1. **No pre-flight validation in boot scripts**: gh auth, branch, Python availability, required files — all unchecked before launching Claude. Boot scripts are pure "launch and hope."

2. **No post-boot confirmation**: boot_remote.py spawns a terminal and returns success. It has no way to know if Claude actually started, loaded CLAUDE.md, passed the gh auth check, and began cycling. The 10-minute cooldown is a blind timer.

3. **No structured health status**: The system uses two independent signals (PID alive + current-state mtime) that were designed for different purposes. There is no single "this agent is healthy/degraded/dead/restarting" status file.

4. **No context-pressure file for PM/QA/DM**: Only the skill agent template includes the disk-write instruction. PM, QA, and DM boot scripts poll for a file that is never written.

5. **No log rotation**: `boot-attempts.log`, `restart-log.txt` grow unbounded. Not a boot failure, but operational hygiene.

6. **No cross-platform kill consistency**: PS1 uses `taskkill /T /F /PID` (kills process tree). sh uses `kill -INT` (sends interrupt to child only, does not kill grandchildren). If Claude spawns subprocesses, the sh version may leave orphans.

## Open Questions

- **Q1**: Should `.health` be written by the boot script wrapper, the agent, or both? — **Why**: If the wrapper writes it, we get boot-level health (alive/restarting/backoff/dead). If the agent writes it, we get cycle-level health (idle/working/stalled). Both are needed. The wrapper should write boot-level status; the agent continues writing `current-state` for cycle-level status. health_check.py reads both.

- **Q2**: Should boot_remote.py verify the agent actually started after spawning? — **Why**: Currently it's fire-and-forget. Adding a post-spawn health poll (wait 30s, check for current-state update) would catch immediate boot failures but add complexity. The cooldown already prevents respawning for 10 minutes. Whether to add this depends on how often "spawn succeeds but agent fails" occurs.

- **Q3**: Should the context-pressure restart be removed from the boot script watcher and left entirely to the agent's self-restart? — **Why**: Currently there are two paths: (a) agent writes `.restart` at cycle end (self-restart), (b) watcher detects pressure file and kills Claude. Path (b) exists as a safety net if the agent fails to self-restart. But path (b) adds complexity and the potential for killing Claude mid-operation. If path (a) is reliable, path (b) could be simplified to just a "hard kill after N minutes of high pressure with no self-restart."

- **Q4**: How should #941 (gh auth + branch checks) interact with #942 (health status)? — **Why**: If pre-flight checks are added to the boot script, failures should be recorded in the health status file so PM knows WHY an agent didn't boot, not just that it didn't.

## Recommendation

**Feasible with caveats.** The core architecture (boot script wrapper + PID detection + sentinel files) is sound. The problems are all fixable without architectural changes:

1. **P0 — Fix the split-brain** (#942): Introduce `.squidsquad/<role>/.health` written by the boot script wrapper with structured status (`booting|alive|restarting|backoff|dead|error`). health_check.py reads this alongside `current-state` mtime. boot_remote.py reads `.health` instead of raw PID checks.

2. **P0 — Add pre-flight checks** (#941): Boot script checks `gh auth status` and `git branch --show-current` before launching Claude. Failures write to `.health` file with error details and exit without entering the restart loop.

3. **P1 — Add context-pressure disk-write to all agents**: Update the `context-pressure` sub-skill template and re-deploy all agents. Currently only skill has it.

4. **P1 — Re-compose QA and DM**: Fix stale wizard references.

5. **P2 — Add log rotation**: Cap `boot-attempts.log` and `restart-log.txt` at 100 entries.

6. **P2 — Cross-platform kill consistency**: Use `kill -TERM` + process group on Linux/Mac to match Windows `taskkill /T /F` behavior.

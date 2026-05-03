Now I have a thorough understanding. Let me compile the audit.

---

# AUDIT-4966-PRD Research — Harness Absorbs Wrapper: PRD Audit

## Summary

This audit examines the PRD for #4966 (harness absorbs wrapper — full agent lifecycle ownership) across 10 dimensions: diagram completeness, acceptance criteria coverage, prose/diagram consistency, implementation sequence ordering, architecture/scenario alignment, Ctrl+C behavior consistency, `.harness-state.json` corruption scenarios, safe-default correctness, power-outage PID recycling, and gaps in the What Gets Removed table.

**Recommendation**: Feasible with caveats. The PRD is architecturally sound and well-researched, and the vault decisions strongly support this direction. However, the audit identified 4 medium-severity gaps (missing crash-recovery diagram, PID recycling unaddressed, no dual-write transition in implementation sequence, `.booting` sentinel missing from removal table) and 2 genuine contradictions (Crash Flow diagram shows instant AutoReboot without backoff vs. prose "configurable policy"; Ctrl+C outcome for harness process is ambiguous between diagrams and prose). These are fixable at PRD level before implementation begins.

## Vault Context

- **BRIEFING.md priorities**: #4439 Harness shipped, #4709 Harness Phase 2 planned, #4221 Agent harness supervisor — this task extends the harness epic directly. All harness priorities are active.
- **Related decisions**: [[decision-pid-primary-liveness]] — "PID is primary for liveness, .health is informational only" — this PRD completes the transition by eliminating .health entirely in favor of direct PID monitoring. Strong alignment; the decision validates the architectural direction.
- **Related decisions**: [[decision-reboot-kills-child]] — `.pid` = wrapper, `.claude-pid` = claude. When harness absorbs wrapper, both collapse into a single harness-tracked PID. The PRD correctly handles this collapse, but the PID discovery challenge (wt.exe fire-and-forget) means the distinction may still exist temporarily via the thin launcher.
- **Related decisions**: [[decision-watchdog-supervisor]] — centralized lifecycle in watchdog.py. The harness absorbing the wrapper makes harness the watchdog. The PRD's intent state machine subsumes watchdog responsibilities, which is correct but means the vault's watchdog decision will be superseded.
- **Related decisions**: [[decision-self-healing-sentinel]] — two-tier self-healing. The API-based intent model eliminates TOCTOU races but introduces a new failure mode (API unreachable). The safe default (continue running) is Tier 1 self-healing — but the PRD doesn't explicitly frame it that way.
- **Human preferences**: "prefer direct/mechanical checks over indirect state files" — the PRD's elimination of ALL sentinel files in favor of API calls and PID monitoring aligns perfectly. Also: "agents stay in visible terminal windows" — the thin launcher + wt.exe approach respects this constraint.
- **Related learnings**: [[learning-powershell-start-job-cwd]] — CWD issues with spawned processes. Relevant because thin launcher must set correct cwd for each clone. The PRD addresses this implicitly via wt.exe `-d` flag.

## Impact Analysis

- **Files touched**: `harness.py` (major rewrite — currently 678 lines at `references/scripts/harness.py`), `cycle_post.py` (lines 444-486, 560-586), `cycle_pre.py` (pre-flight split), `boot_remote.py` (spawn logic changes), `health_check.py` (pid-only liveness), `start_team.py` (sentinel→API migration), `compose.py` (boot subcommand rewrite, lines 922-964), `reboot_agent.py` (absorbed), `squidsquad_cli.py`, `references/templates/start-role.ps1` (deleted), `references/templates/start-role.sh` (deleted), 5 sub-skills updated, all clone-local `start-*.ps1/.sh` deleted
- **Behavior changes**: Wrapper scripts eliminated entirely; all sentinel files eliminated; cycle_post uses HTTP API instead of file reads; harness directly monitors PID (no .health polling); harness spawns via wt.exe + thin launcher; Ctrl+C becomes 3-stage escalation; crash recovery via `.harness-state.json`
- **Dependencies**: FastAPI/uvicorn (already present), wt.exe on Windows, `subprocess.Popen` with `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`, `os.kill(pid, 0)` for liveness

## Side Effects

- **Risk 1**: PID discovery gap with wt.exe fire-and-forget — The harness spawns via wt.exe which returns immediately with wt.exe's PID, not claude's PID. The thin launcher must write claude's PID to a file that harness reads. If the thin launcher fails to write or harness reads before write, the agent is "invisible" to monitoring. — Severity: H — Mitigation: Harness must poll for PID file with timeout after spawn (noted in research but not explicit in PRD acceptance criteria).

- **Risk 2**: `.harness-state.json` becomes the new single point of failure for crash recovery — If corrupted or stale, harness loses all agent state on restart. Currently, agents survive independently with their own sentinel files. — Severity: M — Mitigation: Atomic writes (write .tmp, rename), validate JSON on read, fall back to process scanning if state file is unreadable.

- **Risk 3**: Clone isolation for port discovery — `cycle_post.py` runs in a clone directory (`{clone_path}/references/scripts/`). The `.harness-port` file lives in the primary repo's `.squidsquad/`. The parent-directory walk algorithm must be correct for arbitrary clone depths. — Severity: M — Mitigation: Default port 7373 + parent-dir walk + hard limit on walk depth (already described in PRD section 4).

- **Risk 4**: Generated scripts stale vs templates — Confirmed in codebase: `references/templates/start-role.ps1` (line 1) has full loop architecture but current deployed wrappers may be older. Since both are deleted, this is moot — but compose.py's `boot_role()` (line 922) must stop generating the old template format. — Severity: L — Mitigation: Delete templates, replace boot command with thin launcher generation.

## Edge Cases

- **Harness crash while agent is in cycle_post**: Agent's API call to `GET /agents/{role}` fails → safe default (exit 0, continue). Agent survives, continues next cycle. Harness restart recovers intent from `.harness-state.json`. **Gap**: If harness crashed after setting intent=stopping but before persisting to state file, the stop intent is lost. The PRD's implementation sequence step 2 says "write on spawn/death/intent change" — intent changes must be persisted immediately, not batched.

- **Thin launcher fails to start claude**: Launcher exits with error, PID file never written (or contains error). Harness polls for PID file, times out, marks agent as "error." **Gap**: The PRD doesn't specify what harness does on spawn timeout — retry? backoff? alert operator?

- **Agent process killed externally (Task Manager, SIGKILL)**: Harness PID monitor detects death within HEALTH_POLL_INTERVAL (5s). Intent=running → auto-respawn. This is correctly handled in PRD section 2 and Crash Flow diagram. Edge case: if agent is killed during `cycle_post.py` write (mid-commit), state may be inconsistent — same as current behavior, acceptable.

- **Multiple harness instances**: Port collision prevents second instance from starting (current behavior at `harness.py` line 577-591, `find_free_port`). If port file is stale from crashed harness, new harness binds to different port, writes new port file. Acceptable.

- **`.harness-state.json` doesn't exist on first run**: Harness must handle FileNotFoundError gracefully — initialize empty state and populate from health poll. **Gap**: Not in acceptance criteria.

- **PID recycling after harness restart**: Harness reads `.harness-state.json`, finds PID 12345 for skill agent, checks if alive. PID 12345 now belongs to Chrome.exe (recycled). `os.kill(pid, 0)` succeeds — harness thinks agent is alive. **Gap**: The PRD doesn't address PID recycling. Mitigation: Store process creation time or check process name via `psutil`/`tasklist`.

- **Context pressure exit and intent=stopping race**: Agent detects context pressure locally, exits 42. Simultaneously, operator sets intent=stopping. Harness sees exit 42, intent=stopping. Should harness NOT respawn (stopping wins)? Should it respawn (context pressure was the cause)? **Gap**: The intent state machine in PRD section 3 doesn't prioritize between context-pressure-triggered exit and operator intent. The PRD says "context pressure → exits 42 → harness: respawn → intent=running" — but if intent was just set to stopping by operator, this contradicts.

## Integration Risks

- **start_team.py dual-write period**: Currently writes `.stop-after-cycle` (line 42-46) and `.stop` (line 49-55). After migration, must call harness API. If start_team.py is updated before harness has the API, commands silently fail. **Mitigation**: start_team.py should try API first, fall back to sentinel files for one version — matching the SENTINEL-RESEARCH dual-write approach at `.squidsquad/pm/planning/FEAT-PM-4966-SENTINEL-RESEARCH.md` line 93.

- **reboot_agent.py absorption**: Currently reads `.claude-pid` (line 94-98) and kills claude directly. After harness absorption, harness holds the PID and kills directly. The reboot_agent.py module becomes a thin wrapper or is deleted. **Risk**: If any other script imports reboot_agent (e.g., `start_team.py --force` at line 136-137), those imports break.

- **health_check.py dependency**: Harness currently imports and calls `health_check.check_all_agents()` (harness.py line 122). After migration, harness does direct PID monitoring — but health_check.py may still be called by external tooling. The AC says "updated to query harness API instead of reading .health files (or deprecated)" — this is correct but needs explicit test coverage.

- **compose.py boot subcommand**: Currently generates full wrapper scripts from templates (lines 922-943). After migration, must generate thin launcher. But compose.py's `boot_role()` is also called during initial setup — changing its output format requires all clones to be recomposed. **Risk**: If an agent is running old wrapper when compose is updated, the new thin launcher won't have the loop/respawn logic the old wrapper had — agent becomes unmonitored.

## Upgrade & Migration

- **New config values**: `Harness.CrashBackoffMax` (default: 5), `Harness.HeartbeatInterval` (default: 5) — both mentioned in research but not in PRD proper. The PRD section 2 says "configurable policy" for crash retry but doesn't specify config keys.
- **New files**: `.squidsquad/.harness-state.json` — JSON array of per-agent state (PID, intent, boot_time, clone_path). Thin launcher scripts (new minimal `.ps1`/`.sh` in each clone's `.squidsquad/` directory, replacing current full wrappers).
- **Template changes**: `references/templates/start-role.ps1` — **deleted** (line 1-200+). `references/templates/start-role.sh` — **deleted** (line 1-200+). New thin launcher template needed (or thin launcher generated inline by compose.py without a template file).
- **Upgrade steps**: Stop all agents → deploy new harness → clean stale sentinel files → recompose → start via harness. **Gap**: The upgrade path (PRD acceptance criteria, context doc lines 45-50) doesn't specify what happens to the `.booting` sentinel during cleanup. It also doesn't address agents that are mid-cycle during upgrade.
- **Graceful degradation**: If user doesn't upgrade `cycle_post.py`, harness must continue writing `.stop-after-cycle` as fallback. This dual-write period is described in SENTINEL-RESEARCH (line 92-97) but NOT in the PRD acceptance criteria or implementation sequence. **This is a gap.**

## Open Questions

- **Q1**: What happens when context pressure exit (42) and operator stop intent race? — **Why**: If agent exits 42 for context pressure but operator simultaneously set intent=stopping, the harness must decide: respawn (context pressure wins) or don't (operator intent wins). The PRD state machine doesn't have a priority rule for this. Getting it wrong means either unwanted respawn after operator stop, or lost auto-recovery after context pressure.

- **Q2**: Should `.harness-state.json` store process creation time to detect PID recycling? — **Why**: After power outage + reboot, or harness crash + delayed restart, PIDs can be recycled by the OS. Without creation time or process name verification, harness could attach to a wrong process. The SENTINEL-RESEARCH touches on persistence (line 102-103) but doesn't address recycling detection. Getting this wrong means harness silently monitors the wrong process.

- **Q3**: Does the thin launcher replace or augment the existing wrapper during transition? — **Why**: The implementation sequence (step 5: harness spawn, step 12: delete wrappers) has 7 steps between spawn capability and wrapper deletion. During those 7 steps, both harness-spawned and wrapper-spawned agents could exist. The PRD doesn't specify whether harness can detect and adopt wrapper-spawned agents, or if a clean cutover is required.

- **Q4**: What is the `.booting` sentinel's fate? — **Why**: It's used by `boot_remote.py` (lines 203-253) for concurrent spawn prevention. If harness absorbs spawn responsibility, it either needs its own concurrency control or retains `.booting`. The What Gets Removed table doesn't mention `.booting` — it should either be listed as "eliminated — harness internal mutex" or "kept — harness writes it."

## Recommendation

**Feasible with caveats.** The PRD is thorough and well-aligned with vault decisions. The 6 issues requiring resolution before implementation:

1. **Add a Harness Crash Recovery diagram** — currently missing. Must show: harness restart → read `.harness-state.json` → check PIDs alive → resume monitoring / respawn dead agents with intent=running. This is user story US-9 but has no visual.

2. **Fix Crash Flow diagram** — shows instant AutoReboot without backoff delay. Add a "backoff wait" state between HarnessDetects and AutoReboot, or at minimum note "with configurable backoff" on the transition.

3. **Clarify Ctrl+C end state** — The state diagram shows `GracefulStop → WaitingForInput: 5s timeout (agent exited)`, meaning harness stays running after agents exit. But the prose implies harness exits after agents stop. Decide: does Ctrl+C stop just agents (harness survives) or both (harness exits)? Document the answer consistently.

4. **Address PID recycling in `.harness-state.json`** — Add process creation time or process name to the stored state. Add an AC: "Harness validates stored PIDs are still the correct processes (not recycled)."

5. **Add dual-write transition period to implementation sequence** — Between steps 5 and 12, harness must write both API intent AND `.stop-after-cycle` for backward compatibility with agents running old `cycle_post.py`. Step 7 (update cycle_post.py) should note: "API-first with file-fallback for one version."

6. **Add `.booting` to What Gets Removed table** — Either "eliminated — harness internal mutex replaces it" or "kept — harness writes it during spawn."

The remaining gaps (missing diagram for API failure fallback, safe default edge case with harness crash, `.harness-state.json` corruption scenarios) are lower severity and can be addressed during implementation if documented as known risks.

## Vault Candidates

- **Type**: decision — "API-based intent replaces file-based sentinels; safe default on API failure is continue-running" — **Why**: This is the final sentinel elimination (#3807 → #4966). The safe-default pattern (agent continues if it can't reach harness) is a non-obvious design choice with subtle failure modes worth preserving.
- **Type**: pattern — "Thin launcher PID report-back pattern for wt.exe fire-and-forget" — **Why**: The constraint that wt.exe returns immediately forces a specific pattern: spawn terminal → launcher writes PID to known file → harness polls for file. Reusable for any Windows terminal-based process management.
- **Type**: learning — "Dual-write phase (API + file) enables zero-downtime migration from file-based to API-based signals" — **Why**: The sentinel research documents this pattern at line 92-97. The PRD should explicitly include it in implementation sequence. This migration pattern is reusable for other sentinel-to-API transitions.
- **Type**: learning — "Generated scripts can drift from templates when compose.py boot-all is not run after template changes" — **Why**: Discovered in research: `references/templates/start-role.ps1` has the #3807 loop architecture but actual clone scripts may not. This is a process gap — template changes without regeneration = silent drift. Documented in FEAT-PM-4966-RESEARCH.md.
- **Type**: decision — "Ctrl+C three-stage escalation for graceful agent shutdown" — **Why**: The specific 3-press pattern (graceful → warn → force kill) with 5s timeout is a novel UX pattern for process supervisors. Worth documenting the design rationale and platform considerations (Windows lacks Ctrl+D signaling).
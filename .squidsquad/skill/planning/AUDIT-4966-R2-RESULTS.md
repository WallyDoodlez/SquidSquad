Now I have all the data. Let me compile the comprehensive second audit.

---

# AUDIT-4966-R2 Research — Second Audit: Harness Absorbs Wrapper Implementation

## Summary

This second audit assesses the post-fix state of the #4966 implementation. The dev agent addressed all 6 items flagged in AUDIT-4966-RESULTS.md: (1) Ctrl+C stage 3 now exits harness only, agents survive; (2) `claude_pid` added to `AgentState.__slots__`, `to_dict()`, `save_state()`, and `load_state()`; (3) `update_health()` rewritten with direct-PID-primary + `.claude-pid` file fallback + `health_check.py` legacy fallback; (4) some stale docstrings fixed; (5) 14 `.ps1`/`.sh` wrapper scripts deleted; (6) `compose.py boot_role()` made no-op.

**Primary result**: 11 PASS, 7 FAIL, 5 PARTIAL, 5 non-critical issues discovered. The implementation is significantly improved but still has critical gaps: sentinel files persist in the health-check chain, PID recycling detection is missing, pre-flight gh auth split is not implemented, sub-skills are completely stale, and upgrade documentation is absent. The architecture is sound — the remaining work is completion work, not rethinking.

**Recommendation**: Feasible with caveats — ship with known AC failures gated behind a feature flag, or complete the remaining 7 FAIL items before merge.

## Vault Context

- **BRIEFING.md priorities**: #4439 Harness shipped, #4709 Harness Phase 2 planned — #4966 extends harness lifecycle ownership. No blockers.
- **Related decisions**: [[decision-pid-primary-liveness]] — PID is primary for liveness. The harness now honors this with direct PID checks. **Constraint honored**.
- **Related decisions**: [[decision-reboot-kills-child]] — Wrapper never dies during reboot. The thin launcher has no respawn loop — harness owns restarts via intent state machine. **Constraint honored**.
- **Human preferences**: "just use PID, it's more direct" and "prefer direct/mechanical checks over indirect state files." The harness update_health() now uses direct PID checks as primary — but the fallback chain still reads `.health` and `.claude-pid` files. The `.claude-pid` file is a practical necessity for fire-and-forget terminal spawns. **Partially honored**.
- **Related learnings**: [[learning-powershell-start-job-cwd]] — CWD handling relevant for thin launcher. Current implementation uses `os.getcwd()` from harness/boot_remote spawn CWD — correct.

## Impact Analysis

- **Files touched (code)**:
  - `references/scripts/harness.py` — AgentState gains `claude_pid`, `update_health()` rewritten, `_read_claude_pid()` added, shutdown `_force_kill()` makes agents survive, `save_state()`/`load_state()` include `claude_pid`, `stop_all()` uses API intent
  - `references/scripts/thin_launcher.py` — One-shot launcher (unchanged from first audit)
  - `references/scripts/cycle_post.py` — API intent check via `_query_harness_intent()` (unchanged)
  - `references/scripts/boot_remote.py` — `_find_boot_script()` prefers thin launcher; `_needs_boot()` still sentinel-based (unchanged from first audit)
  - `references/scripts/start_team.py` — Harness API for stop/reboot with sentinel fallback (unchanged)
  - `references/scripts/health_check.py` — Untouched, still sentinel-based
  - `references/scripts/compose.py` — `boot_role()` is no-op
  - `references/scripts/reboot_agent.py` — Has independent `_read_claude_pid()` (duplicated logic)
- **Files touched (tests)**: `test_harness.py` (new PID tests), `test_thin_launcher.py`, `test_cycle_post.py`, `test_start_team.py`, `test_reboot_agent.py`
- **Files touched (docs)**: None — sub-skills NOT updated
- **Deleted**: `references/templates/start-role.ps1`, `references/templates/start-role.sh`, all `start-*.ps1`/`.sh` from `.squidsquad/`
- **Behavior changes**: Ctrl+C stage 3 exits harness only (agents survive); harness tracks `claude_pid` per agent; health polling uses direct PID; compose.py no longer generates wrappers
- **Dependencies**: FastAPI/uvicorn (existing), `urllib.request` (stdlib), `boot_remote._is_process_alive()` (used by harness), `health_check.py` (fallback dependency)

## Acceptance Criteria Audit

### CRITICAL (FAIL)

| # | AC | Status | Detail |
|---|-----|--------|--------|
| 6 | ALL sentinel files eliminated | **FAIL** | `.health` files still present for dm/qa/skill (`.squidsquad/*/.health`). `.pid` files present for dm/pm/qa/skill. `.booting` files present for dm/pm/skill. `.claude-pid` still written by thin launcher (present for skill). `boot_remote._needs_boot()` at line 303-353 reads `.health`, `.pid`, `.stop`, `.booting`. `health_check.py` exclusively reads `.health` files. Harness fallback at line 182-196 reads `.health` and `.stop`. `start_team._write_stop()` at line 74 writes `.stop` sentinel. |
| 8 | PID recycling detection | **FAIL** | Not implemented. `boot_time` is set in `AgentState` and persisted, but no code compares stored `boot_time` against actual process creation time. PRD Scenario 7 requires this for power-outage recovery. |
| 20 | Pre-flight split: harness does gh auth | **FAIL** | No `gh auth` check anywhere in `harness.py` main/lifespan. `cycle_pre.py` still handles git operations but harness startup doesn't verify GitHub auth. |
| 21 | health_check.py updated for harness API | **FAIL** | `health_check.py` is completely untouched — still reads `.health` files exclusively. No harness API integration. Called as fallback by `harness.update_health()` at line 185. |
| 24 | agent-lifecycle.md updated | **FAIL** | Still describes wrapper scripts, `.stop-after-cycle` sentinel, `.pid` singleton lock, `.health` heartbeat written by wrapper every 5s. All stale. |
| 25 | self-restart.md deleted | **FAIL** | Still present at `references/sub-skills/common/self-restart.md`. Describes wrapper-based restart with `.stop-after-cycle` sentinel and wrapper respawn. Should be deleted per PRD Instruction Layer Mapping table. |
| 28 | Upgrade path documented | **FAIL** | No upgrade documentation exists. PRD Context requires 6-step upgrade path. |

### PARTIAL

| # | AC | Status | Detail |
|---|-----|--------|--------|
| 3 | compose.py boot generates thin launcher | **PARTIAL** | `boot_role()` is a no-op — correct that it doesn't generate wrappers, but it doesn't generate thin launcher either. The thin launcher is standalone at `references/scripts/thin_launcher.py` and is discovered by `boot_remote._find_boot_script()`. Acceptable but AC says "generates thin launcher." |
| 22 | boot_remote.py updated for harness API | **PARTIAL** | `_find_boot_script()` prefers thin launcher (✅), but `_needs_boot()` (lines 303-353) is 100% sentinel-based, and the module docstring (lines 4-8) still describes `.health` as primary with PID fallback. |
| 26 | cycle-runner.md updated | **PARTIAL** | Line 68 still says "restart sentinels" and line 57 still has `"restart_needed": false` in the example JSON. Does not mention harness API intent check. |
| 27 | All tests updated | **PARTIAL** | Good coverage on state model, intent lifecycle, cycle_post API checks. Missing: Ctrl+C escalation tests, thin_launcher `main()` end-to-end, health poll with all three detection paths tested independently, harness `update_health()` with health_check fallback exercised without mocking it entirely. |
| 14 | Crash recovery from .harness-state.json | **PARTIAL** | `load_state()` restores `claude_pid` and intent, and health poll validates PIDs on next cycle (✅). But on restart, if harness was killed while an agent was alive, `load_state()` restores a stale PID that may be recycled. Without PID recycling detection (AC 8), the harness could wrongly think a recycled PID is the old agent. |

### PASS

| # | AC | Status | Detail |
|---|-----|--------|--------|
| 1 | All start-*.sh/.ps1 deleted | **PASS** | Glob for `.squidsquad/start-*.ps1` and `.squidsquad/start-*.sh` returns no matches. |
| 2 | Template wrappers deleted | **PASS** | Glob for `references/templates/start-*.*` returns no matches. |
| 4 | Harness spawns via thin launcher | **PASS** | `boot_remote._find_boot_script()` at line 382-384 prefers `thin_launcher.py`. Harness endpoints call `boot_remote.boot_agent()`. |
| 5 | Thin launcher writes PID → harness reads it | **PASS** | `thin_launcher._write_pid()` writes `.claude-pid` at line 75. Harness `_read_claude_pid()` reads it at line 123. `update_health()` uses stored `claude_pid` (line 168) then falls back to file (line 175). |
| 7 | .harness-state.json tracks PIDs, intents, boot_time | **PASS** | `save_state()` at line 267 includes `claude_pid` per agent. `load_state()` at line 295 restores it. Verified in test at line 98. |
| 9 | Intent state machine correct | **PASS** | States `running`/`stopping`/`restarting`/`stopped` with correct transitions. Tested in `TestIntentLifecycle`. |
| 10 | cycle_post.py queries API for intent | **PASS** | `_query_harness_intent()` at line 478 calls `GET /agents/{role}`. |
| 11 | Safe default on API failure | **PASS** | `_query_harness_intent()` returns `None` on failure (line 494-496), `_do_stop_after_cycle_check()` treats `None` as continue (line 511-514). |
| 12 | Port discovery in cycle_post | **PASS** | `_discover_harness_port()` at line 446 — default 7373 + parent-dir walk for `.harness-port`. |
| 13 | Auto-reboot on unexpected death | **PASS** | `update_health()` at lines 216-225: detects dead agent with `intent=running` or `restarting`, triggers `boot_remote.boot_agent()`. |
| 15 | GET /agents/{role}/health | **PASS** | Endpoint at line 540 returns alive/status/phase/context_pressure from current-state and context-pressure files. |
| 16 | GET /agents/{role}/config | **PASS** | Endpoint at line 577 reads config.md via config.py. |
| 17 | Ctrl+C escalation | **PASS** | Stage 1 sets intents and raises KeyboardInterrupt. Stage 2 warns. Stage 3 calls `os._exit(1)` — exits harness only, agents survive (line 847-855). |
| 18 | Context pressure + operator intent priority | **PASS** | `_do_stop_after_cycle_check()` at line 511 checks harness intent first; operator intent (`stopping`/`restarting`) returns True immediately. Context pressure is secondary check (line 531). |
| 19 | First-run state file missing → no error | **PASS** | `load_state()` at line 301 returns early if file missing. |
| 23 | start_team.py updated for harness API | **PASS** | `cmd_stop()` calls harness `POST /agents/{role}/stop` (line 167), `cmd_reboot()` calls `POST /agents/{role}/restart` (line 154). Sentinel fallback when harness unreachable (line 171). |

## Side Effects & Non-Critical Issues

- **N1: harness.py module docstring is stale** — Severity: **L** — Lines 8-11: "Reads sentinel files (.pid, .claude-pid, .health) for state — does NOT own PIDs." Code now directly owns PIDs via `AgentState.claude_pid` and direct PID checks. Misleading to maintainers. **Mitigation**: Update docstring to reflect PID ownership.

- **N2: boot_remote.py module docstring is stale** — Severity: **L** — Lines 4-8: "Detection uses .health file (primary) with PID fallback" and "polls .health for up to 30s." Still describes old architecture even though `_find_boot_script()` now prefers thin launcher. **Mitigation**: Update docstring.

- **N3: `_read_claude_pid()` duplicated across modules** — Severity: **L** — `reboot_agent._read_claude_pid()` (line 93-105) and `harness.HarnessState._read_claude_pid()` (line 123-135) implement identical logic with subtle differences: `reboot_agent` takes `Path` clone_path, `harness` takes `str` clone_path. `reboot_agent` version is also used by `harness.py` `/shutdown` endpoint at line 700. **Mitigation**: Consolidate into `boot_remote.py` (which already has `_read_pid_file()` at line 153) and have both modules import it.

- **N4: Auto-reboot leaves 5-second PID visibility gap** — Severity: **L** — When `update_health()` triggers auto-reboot at line 241, it sets `agent.claude_pid = None` (line 224) then calls `boot_remote.boot_agent()`. The new PID isn't known until the next health poll cycle (up to 5s) reads the `.claude-pid` file at line 175. During this window, the agent is running but harness has no PID. **Mitigation**: After `boot_agent()` returns, immediately read `.claude-pid` and store it. Or have `boot_agent()` return the new PID.

- **N5: `/shutdown` endpoint kills agents — contradicts PRD Scenario 4 spirit** — Severity: **L** — Lines 700-703 in `/shutdown` handler call `reboot_agent._kill_process()` after waiting for idle. PRD Scenario 4 says "agents survive in their terminals" on harness exit. The `/shutdown` endpoint is explicitly a "stop all agents then exit" operation, so this may be intentional, but it conflicts with the principle that harness exit should not kill agents. **Mitigation**: Either document `/shutdown` as the "force stop + kill" path vs Ctrl+C as the "exit harness, agents survive" path, or make `/shutdown` also leave agents running.

- **N6: `boot-remote-agents.md` sub-skill is stale** — Severity: **L** — Line 16: "Agent lifecycle is managed by `start_team.py` and the wrapper scripts." Should reference harness. Not in the PRD acceptance criteria explicitly, but in the Instruction Layer Mapping table, the PRD says "PM queries harness `/agents/{role}/health` API instead of reading .health files." **Mitigation**: Update or note as out-of-scope.

- **N7: `health-check.md` PM sub-skill not verified** — Severity: **L** — Exists at `references/sub-skills/roles/pm/health-check.md`. Not listed in PRD Instruction Layer Mapping but may need updating. **Mitigation**: Review and update to reference harness API.

## Edge Cases

- **PID recycling on harness restart**: `load_state()` restores `claude_pid` from state file. If the harness was down for hours and the OS recycled that PID to an unrelated process, `_is_process_alive()` returns True for the wrong process. Without creation-time validation, harness resumes monitoring a random process. **Risk**: Medium. Only manifests if harness is down for duration exceeding OS PID wrap.

- **Thin launcher exits before harness reads PID**: Thin launcher writes `.claude-pid` then waits for claude (line 79-80). Harness reads `.claude-pid` from within the 5s health poll cycle. If claude crashes before the first health poll, `.claude-pid` is cleared by thin launcher's `_clear_pid()` (line 90). Harness sees no PID → falls back to `health_check.py` → may detect "unknown" → correct behavior.

- **Harness crashes between `save_state()` and agent spawn**: `save_state()` is called after setting `status=starting` in `start_agent()` (line 534). If harness crashes, `load_state()` restores `status=starting` but no `claude_pid` yet. On restart, `update_health()` checks PID for that role → `.claude-pid` exists from thin launcher → picks it up. **Correct**.

- **Multiple harness instances racing on `.harness-state.json`**: `save_state()` uses atomic write-then-rename. Two harnesses could interleave reads and writes, but they'd only compete if running concurrently on the same machine — a misconfiguration. Same risk exists for `.harness-port`.

- **Thin launcher spawned in wrong CWD**: `boot_remote._spawn_terminal()` passes `cwd=str(clone_root)`. Thin launcher reads `os.getcwd()` at line 56. If the spawn doesn't honor `cwd` (e.g., Windows Terminal startup directory override), thin launcher writes `.claude-pid` to the wrong path. **Risk**: Low — already tested in the wild.

## Integration Risks

- **R1: health_check.py remains the PM's primary health probe** — `boot-remote-agents.md` sub-skill directs PM to read `boot_results` from `cycle-input.json`. `cycle_pre.py` calls `boot_remote.boot_all()` which uses `_needs_boot()` — still 100% sentinel-based. PM agents querying health will get sentinel-derived results even when harness is running. **Severity**: M.

- **R2: `reboot_agent.py` is not integrated with harness intent API** — `reboot_agent.reboot()` (line 108) writes `.restart` sentinel and kills claude PID, expecting wrapper to detect and respawn. With thin launcher, there is no wrapper respawn loop — the `.restart` sentinel is ignored. If `reboot_agent.py` is called directly (not via harness API), the agent is killed but never restarted. **Severity**: H (only if called directly). The harness `/restart` endpoint sets intent in-memory and lets the health poller handle respawn — correct path. But `reboot_agent.py` CLI is still usable by operators and would break agents.

- **R3: `start_team.py` fallback writes `.stop` sentinel** — When harness is unreachable, `cmd_stop()` writes `.stop` sentinel at line 172. The harness `update_health()` at line 206-208 checks for `.stop` and marks agent as stopped. But `boot_remote._needs_boot()` at line 312-314 also checks `.stop` and refuses to boot. These two `.stop` readers are consistent. However, if the harness later becomes available, the only way to clear `.stop` is `start_team.py --boot` which calls `_remove_stop()` (line 85), or manual deletion. No harness API endpoint clears `.stop`. **Severity**: L.

## Upgrade & Migration

- **New config values**: None required. `harness-enabled` and `harness-port` already in config.md `## Harness` section.
- **New files**: `references/scripts/thin_launcher.py` (already exists)
- **Template changes**: Wrapper templates deleted. Thin launcher is standalone, not template-generated.
- **Upgrade steps**: PRD Context specifies 6 steps. Steps 1 (stop agents) and 2 (deploy) are manual. Step 3 (clean stale sentinels) requires deleting `.health`, `.pid`, `.claude-pid`, `.restart`, `.stop`, `.booting` from all clones — not automated. Step 4 (recompose) would regenerate CLAUDE.md with stale sub-skills. Step 5 (delete start scripts) is done. Step 6 (start via harness) works.
- **Graceful degradation**: If harness not running, `start_team.py` falls back to `.stop` sentinel (line 171-172). `cycle_post.py` continues on API failure. `boot_remote.boot_agent()` spawns via thin launcher and old `.health`/`.pid`/`.booting` sentinels are still written by legacy agents. Transition is survivable but messy — sentinel files from old and new systems coexist.

## Open Questions

- **Q1: Should sentinel files be deleted as part of the code change, or as part of the upgrade process?** — **Why**: The AC says "ALL sentinel files eliminated" but the implementation still reads them for backward compatibility. If we delete the reading code, legacy agents break. If we keep the reading code, the zero-sentinel goal is not achieved. The PRD implementation sequence step 17 says "(Next version) Remove .stop-after-cycle file fallback" — suggesting a phased approach. Needs explicit decision.

- **Q2: Is the `/shutdown` endpoint supposed to kill agents or leave them?** — **Why**: PRD Scenario 4 says agents survive harness exit. The Ctrl+C path honors this. The `/shutdown` endpoint kills agents (lines 700-703). This inconsistency could surprise operators. Clarify intent.

- **Q3: Should `reboot_agent.py` be deprecated/removed as part of this task?** — **Why**: The harness owns restarts now. `reboot_agent.py` uses sentinel-based restart that only works with wrappers (`.restart` file). If called directly, it breaks thin-launcher-spawned agents. Either update it to use harness API or mark deprecated.

## Recommendation

**Feasible with caveats.** The core architecture is correct and the 6 items from the first audit are fixed. The remaining gaps are primarily in documentation (sub-skills, upgrade path), one missing feature (PID recycling), and the sentinel-file elimination which is architecturally a phased migration rather than a big-bang deletion. The critical path for shipping is:

1. **Gate**: PID recycling detection (AC 8) — needed for production crash recovery
2. **Gate**: sub-skill updates (AC 24, 25, 26) — stale docs will cause agent misbehavior
3. **Gate**: upgrade path documented (AC 28)
4. **Optional for this PR**: health_check.py migration (AC 21), boot_remote.py migration (AC 22), full sentinel elimination (AC 6) — these can follow the PRD's phased approach (step 17: next version removes fallback)
5. **Non-critical fixes**: stale docstrings (N1, N2), duplicated `_read_claude_pid()` (N3), auto-reboot PID gap (N4), `/shutdown` consistency (N5), `reboot_agent.py` deprecation (Q3)

## Vault Candidates

- **Type**: decision — "Sentinel elimination is a phased migration, not a big-bang deletion" — **Why**: The PRD says "ALL sentinel files eliminated" but practical backward compatibility requires a transition period. This tension between architectural purity and operational safety is worth documenting as a design principle for future phased migrations.

- **Type**: learning — "Docstring staleness is the #1 recurring audit finding across all migrations" — **Why**: Both audits found stale docstrings in `harness.py` and `boot_remote.py`. The module-level docstring in `harness.py` (lines 8-11) still says the opposite of what the code does. A pattern of "audit docstrings as a separate checklist step" would prevent this recurring issue.

- **Type**: pattern — "Three-tier health detection: stored PID → .claude-pid file → legacy fallback" — **Why**: The `update_health()` cascade in `harness.py` (lines 167-196) is a clean pattern for phased migration: try the new thing, fall back to the transition mechanism, then fall back to the legacy mechanism. Reusable for any migration where old and new systems coexist.

- **Type**: learning — "Fire-and-forget terminal spawns require a PID-report-back mechanism; `.claude-pid` is communication, not a sentinel" — **Why**: The thin launcher must communicate the claude PID to the harness, and a one-line file is the simplest mechanism. Distinguishing "communication mechanism" (`.claude-pid`, `.harness-port`) from "sentinel" (`.health`, `.stop`, `.restart`) prevents semantic confusion in future PRD writing.

- **Type**: decision — "`reboot_agent.py` is deprecated — harness API is the only supported restart path" — **Why**: The old sentinel-based restart (`.restart` file → wrapper respawn) doesn't work with thin-launcher-spawned agents. `reboot_agent.py` should either be updated to call harness API or marked deprecated with a clear warning. This decision gates whether to fix or delete it.
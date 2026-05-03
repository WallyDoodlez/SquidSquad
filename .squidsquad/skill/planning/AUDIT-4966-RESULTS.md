Now I have all the information needed. Let me compile the comprehensive audit.

---

# AUDIT-4966 Research — Harness Absorbs Wrapper: Full Agent Lifecycle Ownership

## Summary

This audit assesses the work-in-progress implementation of #4966 across two cycles. The codebase shows a **partial, transitional state**: the harness intent API, state persistence, and Ctrl+C escalation are implemented in `harness.py`; `cycle_post.py` queries the harness API for intent instead of reading `.stop-after-cycle` files; `start_team.py` redirects to harness API; and a thin launcher exists. However, the implementation is **approximately 40% complete** — the wrapper scripts, sentinel-file health checking, and sub-skill documentation still reflect the old architecture. Several acceptance criteria are not met, and critical integration gaps exist between the thin launcher (which doesn't write `.health`) and the harness health poller (which exclusively reads `.health`).

**Recommendation**: Needs rethinking — the work-in-progress is architecturally sound but has significant integration gaps and incomplete migration that make it non-shippable. The most critical gap is that the harness health polling chain (`health_check.py` → `boot_remote._needs_boot()`) still relies entirely on sentinel files (`.health`, `.pid`, `.stop`, `.booting`), while the thin launcher only writes `.claude-pid`. The harness cannot detect or monitor thin-launcher-spawned agents until health_check.py is migrated to harness-API-based or direct-PID-based health checks.

## Vault Context

- **BRIEFING.md priorities**: #4439 Harness shipped, #4709 Harness Phase 2 planned — #4966 sits between these, extending harness lifecycle ownership
- **Related decisions**: [[decision-pid-primary-liveness]] — PID is primary for liveness. The current implementation still relies on `.health` files for health polling; this decision isn't yet honored in the health-check chain. **Constraint**: the harness must use direct PID checks, not `.health` files.
- **Related decisions**: [[decision-reboot-kills-child]] — Wrapper never dies during reboot; harness absorbs wrapper. The thin launcher replaces the wrapper but the distinction between `.pid` (wrapper) and `.claude-pid` (claude) persists because the thin launcher still writes `.claude-pid`. **Constraint**: need to decide whether one PID file per agent is sufficient.
- **Human preferences**: "just use PID, it's more direct" and "prefer direct/mechanical checks over indirect state files." The thin launcher writes `.claude-pid` — a sentinel file — contradicting the zero-sentinel goal. The harness health poller uses `.health` files — also contradicting.
- **Related learnings**: [[learning-powershell-start-job-cwd]] — CWD issues with spawned processes; relevant for thin launcher cwd handling.

## Impact Analysis

- **Files touched**:
  - `references/scripts/harness.py` — Intent API, state persistence, Ctrl+C escalation, health/config endpoints **(partially complete)**
  - `references/scripts/cycle_post.py` — API-based intent check, port discovery **(complete)**
  - `references/scripts/start_team.py` — Harness API migration with sentinel fallbacks **(complete)**
  - `references/scripts/thin_launcher.py` — New one-shot launcher **(complete)**
  - `references/scripts/boot_remote.py` — Prefers thin launcher in `_find_boot_script()` **(partial — health detection still sentinel-based)**
  - `references/scripts/health_check.py` — **Not yet migrated** to harness API or PID-only checks
  - `references/scripts/compose.py` — `boot_role()` still generates wrapper templates, not thin launcher
  - `references/templates/start-role.ps1` / `.sh` — **Not deleted** (acceptance criteria requires deletion)
  - `.squidsquad/start-*.ps1` / `.sh` (12 files) — **Not deleted**
  - `references/sub-skills/common/agent-lifecycle.md` — **Not updated** (still describes sentinel/wrapper model)
  - `references/sub-skills/common/self-restart.md` — **Not updated or deleted** (PRD says delete)
  - `references/sub-skills/common/cycle-runner.md` — **Not updated** (still references `restart_needed`)
  - `tests/test_harness.py` — State persistence, intent lifecycle **(good coverage)**
  - `tests/test_cycle_post.py` — API intent check, port discovery **(good coverage)**
  - `tests/test_start_team.py` — Harness API migration **(good coverage)**
  - `tests/test_thin_launcher.py` — PID file operations **(minimal — no main() test)**

- **Behavior changes**:
  1. `cycle_post.py` queries `GET /agents/{role}` for intent instead of reading `.stop-after-cycle` file ✅
  2. Harness stop/restart endpoints set in-memory intent, not file sentinels ✅
  3. `start_team.py` calls harness API for stop/reboot, not writing sentinels directly ✅
  4. Thin launcher replaces wrapper scripts as spawn target ✅
  5. Harness writes `.harness-state.json` on state changes ✅
  6. Crtrl+C three-stage escalation installed ✅
  7. Health check chain **still relies on sentinel files** ❌

- **Dependencies**:
  - FastAPI + uvicorn (existing)
  - `urllib.request` for `cycle_post.py` API calls (stdlib, already used)
  - `boot_remote._spawn_terminal()` for thin launcher terminal spawning (existing)
  - `health_check.check_all_agents()` for harness health polling (not yet migrated)

## Side Effects

- **Risk 1: Thin launcher doesn't write `.health` → harness can't detect agent liveness** — Severity: **H** — The thin launcher writes `.claude-pid` but NOT `.health`. The harness's `update_health()` (line 122) calls `health_check.check_all_agents()` which returns "healthy" based on `.health` heartbeat or `.health=alive`. A thin-launcher-spawned agent writes neither — it has no heartbeat background job. The next health poll will classify it as "unknown" (via mtime fallback). If `current-state` mtime is recent, it may be classified healthy, but this is fragile. **Mitigation**: Either (a) the thin launcher must write `.health` as a heartbeat (contradicting zero-sentinel goal), or (b) `health_check.py` and harness `update_health()` must be rewritten to use direct PID checks via `.claude-pid` or the harness process table.

- **Risk 2: `.claude-pid` is still a sentinel file** — Severity: **M** — The PRD says "ALL sentinel files eliminated: .health, .pid, .claude-pid, .stop, .stop-after-cycle, .restart, .booting." The thin launcher writes `.claude-pid` (line 33 of `thin_launcher.py`) — this is a sentinel file. The PRD's acceptance criteria contradicts the practical need to communicate PID from a fire-and-forget terminal spawn. **Mitigation**: Accept that `.claude-pid` is a communication mechanism (not a sentinel), or replace with HTTP callback from thin launcher to harness (more complex). Update PRD to clarify PID-reporting is not "sentinel."

- **Risk 3: Ctrl+C stage 3 force-kills agents — contradicts PRD** — Severity: **H** — The PRD Scenario 4 says "Agents survive in their terminals" after triple Ctrl+C. The implementation in `CtrlCHandler._force_kill()` (line 785-810) calls `reboot_agent._kill_process()` on each agent's claude PID. Similarly, the `/shutdown` endpoint kills agents (lines 636-641). **Mitigation**: Remove force-kill from stage 3 Ctrl+C and shutdown. Instead, just exit the harness (agents in independent terminals survive). Stage 3 should only kill if the human explicitly requested kill, not default.

- **Risk 4: `compose.py boot` still generates legacy wrappers** — Severity: **M** — `boot_role()` (line 922) generates `start-role.ps1`/`.sh` from the old templates. It doesn't generate or deploy the thin launcher. Running `compose.py deploy-all` after this change would deploy CLAUDE.md files with updated sub-skills but still generate old wrapper scripts — a confusing half-migration. **Mitigation**: Update compose.py to either stop generating wrappers or generate thin launcher deployment.

- **Risk 5: Harness state file doesn't include PIDs** — Severity: **M** — The `.harness-state.json` stores `intent`, `status`, `boot_time`, `clone_path` but no `pid` or `claude_pid` field. On harness restart, `load_state()` can restore intent but cannot rediscover agent PIDs — it relies on the health poll loop to find them via `health_check.py`. If `health_check.py` can't find agents (thin launcher doesn't write `.health`), the harness loses track entirely. **Mitigation**: Store `claude_pid` in `.harness-state.json` and use direct PID liveness checks on restart.

- **Risk 6: Stale docstrings mislead maintainers** — Severity: **L** — `harness.py` docstrings for `stop_all` (line 402), `stop_agent` (line 537), `restart_agent` (line 554) still say "write .stop-after-cycle." `start_team.py` help text (line 201) says "write .stop-after-cycle." The code no longer does this.

## Edge Cases

- **Thin launcher but old wrapper still present**: `boot_remote._find_boot_script()` prefers thin launcher. If thin launcher exists in a clone, the old `start-*.ps1` is ignored. But if `compose.py` regenerates old wrappers, they'll conflict. Boot logic is correct (prefers thin), but stale files create confusion. **Handle by**: deleting old wrappers as part of upgrade.

- **Harness crashes after setting intent=stopping but before agent queries API**: `cycle_post.py` calls `_query_harness_intent()` which returns `None` on failure (line 494). Safe default: continue running. The stop command is silently lost — operator must re-issue after harness restart. **Acceptable** per PRD research conclusion.

- **Context pressure exit + intent=stopping race**: If intent is set to "stopping" between `cycle_pre.py` and `cycle_post.py`, the API check (line 511) sees the current intent. The operator intent wins over context pressure because context pressure check (line 532) only returns True when `exceeded=True`, and both paths independently return True to exit 42. But if intent=stopping AND pressure exceeded, exit 42 triggers — harness sees intent=stopping → no respawn. **Correct behavior.**

- **PID recycling**: The harness state file stores `boot_time` (line 222) but the actual value is always `None` (confirmed in `.harness-state.json` sample). PID recycling detection (comparing stored boot_time against process creation time) is mentioned in the PRD but not implemented.

- **Multiple harness instances**: `find_free_port()` handles port collision. But if second harness starts, it reads `.harness-state.json` and restores agents — both harnesses now monitor the same agents. The port file is a singleton lock only if first harness still holds the port. **Not a regression** (same as old system).

- **Thin launcher on cloned repo without thin_launcher.py**: `boot_remote._find_boot_script()` checks `clone_root / "references" / "scripts" / "thin_launcher.py"`. If the clone doesn't have this file (e.g., old clone), it falls back to legacy wrappers. **Correct degradation.**

## Integration Risks

- **health_check.py not migrated**: The harness health poll loop, PM cycle_pre agent health queries, QA cycle_pre agent health queries, and start_team.py all depend on `health_check.py` output. Until it's migrated to direct PID checks or harness API, the entire health chain is sentinel-dependent. This is the biggest integration risk — it undermines the zero-sentinel goal.

- **Wrapper templates still used by compose.py**: All 12 `start-*.ps1`/`.sh` files in `.squidsquad/` are still present. If an operator runs `compose.py boot-all`, old wrappers are regenerated. The thin launcher exists but is never deployed to clones by compose.

- **agent-instructions.md references are stale**: `references/agent-instructions.md` (generated by `compose.py all`) still describes `.stop-after-cycle` sentinel files and wrapper-based lifecycle. Agents reading this will behave incorrectly with the new system.

- **boot_remote.py duality**: `boot_remote.py` does two contradictory things: (a) prefers thin launcher for spawning (line 382-384), (b) uses sentinel files exclusively for health detection (`_needs_boot()`, lines 303-353). This is the transition state but causes confusion about what's authoritative.

## Upgrade & Migration

- **New config values**: None required. `harness-enabled` and `harness-port` already exist in config.md.
- **New files**: 
  - `references/scripts/thin_launcher.py` — new one-shot launcher
  - `.squidsquad/.harness-state.json` — crash recovery state (created at runtime)
- **Template changes**: 
  - `references/templates/start-role.ps1` / `.sh` — should be **deleted** but still exist
  - New thin launcher is standalone, not template-generated
- **Upgrade steps**: PRD specifies 6-step upgrade path. Currently, step 3 (clean stale sentinels) and step 5 (delete start scripts) are **not executed**. Step 4 (recompose) would generate wrong output.
- **Graceful degradation**: If harness is not running, `start_team.py` falls back to `.stop` sentinel (line 171-172) and `boot_remote.boot_agent()` spawns old wrappers (if thin launcher missing from clone). Transition is survivable but messy.

## Open Questions

- **Q1: Should `.claude-pid` be considered a sentinel or a communication mechanism?** — **Why**: The PRD says "ALL sentinel files eliminated" including `.claude-pid`. But the thin launcher must communicate PIDs to the harness — there's no practical alternative without a callback API. Getting this wrong means either breaking the zero-sentinel promise or having no PID visibility.

- **Q2: Should Ctrl+C stage 3 kill agents or leave them running?** — **Why**: The PRD says "agents survive in their terminals" on harness exit. The code kills them. The human's stated preference is for agents to be recoverable — killing them contradicts that. But leaving orphaned claude processes on force-exit may cause issues. Resolution needed.

- **Q3: How does the harness detect thin-launcher-spawned agents without `.health` files?** — **Why**: The current health poll chain reads `.health` files exclusively. The thin launcher doesn't write `.health`. Without resolving this, the harness is blind to its own spawned agents. This is the single most important integration gap.

- **Q4: Should compose.py stop generating wrapper scripts now or after full migration?** — **Why**: If compose continues generating old wrappers, operators will have both old and new systems present — confusion and potential double-boot. But if compose stops generating wrappers before thin launcher is fully integrated, operators have no boot mechanism.

## Recommendation

**Needs rethinking.** The implementation is architecturally correct but incomplete and contradictory. The key issues:

1. **Health poll chain is the blocker**: `health_check.py` → `harness.update_health()` → `boot_remote._needs_boot()` is the critical path for all agent monitoring, and it's 100% sentinel-file-dependent. Until this chain is rewritten to use direct PID checks or harness API, no other migration matters — the harness can't monitor its own agents.

2. **The thin launcher + `.claude-pid` is a practical compromise** but must be explicitly accepted as a communication mechanism, not a sentinel. Document this exception.

3. **Ctrl+C stage 3 kills agents** — contradicts the PRD and human's preference. Must be changed to just exit harness.

4. **Remaining work is substantial** (see below).

### Remaining Work Checklist (from acceptance criteria):

| # | AC item | Status |
|---|---------|--------|
| 1 | All start-*.sh/.ps1 deleted | ❌ 12 files still present |
| 2 | Template wrappers deleted | ❌ Both still in `references/templates/` |
| 3 | `compose.py boot` generates thin launcher | ❌ Still generates old wrappers |
| 4 | Harness spawns via thin launcher | ⚠️ Thin launcher exists, boot_remote prefers it, but health poll can't see spawned agents |
| 5 | Thin launcher writes PID → harness reads it | ⚠️ Writes `.claude-pid` but harness never reads it (uses health_check) |
| 6 | ALL sentinel files eliminated | ❌ `.claude-pid` still written; `.health`/`.pid`/`.stop`/`.booting` still read |
| 7 | `.harness-state.json` tracks PIDs, intents, boot_time | ⚠️ Tracks intent/boot_time/clone_path but NOT PIDs |
| 8 | PID recycling detection | ❌ `boot_time` stored as null; no creation-time validation |
| 9 | Intent state machine correct | ✅ `running`/`stopping`/`restarting`/`stopped` transitions correct |
| 10 | `cycle_post.py` queries API for intent | ✅ Implemented with safe default |
| 11 | Safe default on API failure | ✅ Returns None → treated as "continue" |
| 12 | Port discovery in cycle_post | ✅ Default 7373 + parent-dir walk |
| 13 | Auto-reboot on unexpected death | ✅ Intent=running + dead → reboot |
| 14 | Crash recovery from `.harness-state.json` | ⚠️ Restores intent but can't verify PIDs |
| 15 | `GET /agents/{role}/health` | ✅ Implemented (reads current-state + context-pressure files) |
| 16 | `GET /agents/{role}/config` | ✅ Implemented (reads config.md) |
| 17 | Ctrl+C escalation | ⚠️ Stage 3 kills agents (should leave running) |
| 18 | Context pressure + operator intent priority | ✅ Operator intent wins (stopping → no reboot) |
| 19 | First-run state file missing → no error | ✅ `load_state()` returns on missing file |
| 20 | Pre-flight split: harness does gh auth | ❌ Not implemented — still in wrapper templates |
| 21 | `health_check.py` updated for harness API | ❌ Not started |
| 22 | `boot_remote.py` updated for harness API | ❌ Still sentinel-based |
| 23 | `start_team.py` updated for harness API | ✅ Implemented |
| 24 | `agent-lifecycle.md` updated | ❌ Not updated |
| 25 | `self-restart.md` deleted | ❌ Still present and stale |
| 26 | `cycle-runner.md` updated | ❌ Not updated |
| 27 | All tests updated | ⚠️ Good coverage on new code; missing coverage on health poll chain, Ctrl+C, thin launcher main |
| 28 | Upgrade path documented | ❌ Not done |

## Vault Candidates

- **Type**: decision — "Thin launcher PID-reporting is a communication mechanism, not a sentinel" — **Why**: The PRD demands zero sentinel files, but the visible-terminal constraint forces a PID-report-back pattern. Distinguishing "communication mechanism" from "sentinel" (file that gates behavior) prevents semantic confusion. Future contributors need to know `.claude-pid` is a necessary bridge, not a sentinel to be eliminated.

- **Type**: learning — "Health poll chain must be migrated first — it's the critical path for all other harness migrations" — **Why**: The current WIP implements intent API and thin launcher but leaves health_check.py untouched. The harness can spawn agents it cannot see. This ordering dependency (health polling must be direct-PID before spawn mechanism changes) is worth documenting for future phased migrations.

- **Type**: pattern — "Three-stage Ctrl+C with increasing severity" — **Why**: The `CtrlCHandler` pattern (stage 1: graceful, stage 2: warn, stage 3: force) is a reusable UI pattern for any long-running supervisor process. Worth capturing if the stage-3 behavior is corrected to "exit harness only."

- **Type**: learning — "Docstring staleness is a regression risk when code and comments diverge during migration" — **Why**: `harness.py` docstrings still say "write .stop-after-cycle" while the code sets in-memory intent. Multiple functions affected. This kind of divergence during phased migrations causes confusion for the next developer. A pattern of "update docstrings in the same commit as behavior changes" would prevent this.

- **Type**: decision — "boot_remote dual role during migration (launcher + health checker)" — **Why**: `boot_remote.py` currently does two things: spawn agents (preferring thin launcher) and detect liveness (via sentinel files). These are splitting into harness-owned responsibilities. Documenting the split point helps future contributors understand the migration state.
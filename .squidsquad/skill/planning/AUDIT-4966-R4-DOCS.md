Now I have all the data. Let me compile the final research document.

---

# AUDIT-4966-R4-DOCS Research — Harness Absorbs Wrapper: Docs, Sub-Skills, Tests

## Summary
This audit reviewed 8 target files (3 sub-skill docs, 1 upgrade doc, 4 test files) against the actual harness source code (`harness.py`, `cycle_post.py`, `start_team.py`, `thin_launcher.py`, `boot_remote.py`). **The new sub-skill files in `references/sub-skills/common/` are accurate** against code behavior. However, **the compose output `references/agent-instructions.md` still contains stale pre-#4966 wrapper-era content** (`.stop-after-cycle` sentinel, `.health` heartbeat, wrapper references at lines 803–863). Additionally, **4 source sub-skill files outside the review list still reference wrapper/health-file patterns**. The upgrade doc has a critical inaccuracy: it instructs users to delete `.claude-pid` and `.booting` sentinels, both of which are still written by the new system. Test coverage is solid for core paths but has gaps in code-42 exit testing, Ctrl+C escalation, `thin_launcher.main()`, and `start_team.cmd_boot`.

**Recommendation**: FAIL — must fix the stale agent-instructions.md, wrong sub-skill source files, and the upgrade doc inaccuracies before this can ship.

## Vault Context
- **BRIEFING.md priorities**: #4439 (Harness epic shipped), #4221 (Agent harness — supervisor process), #4709 (Harness Phase 2 planned)
- **Related decisions**: [[decision-reboot-kills-child]] — critical: `.pid` = wrapper, `.claude-pid` = claude; but #4966 removes wrapper entirely, so `.pid` is deleted and `.claude-pid` is now the sole PID file
- **Related decisions**: [[decision-pid-primary-liveness]] — PID-first liveness, `.health` is informational only. #4966 extends this: harness does direct PID check, `.health` is removed
- **Human preferences**: "Never ship with failed TCs", "Documents live on forge, not chat", "Prefers direct/mechanical checks over indirect state files" — all align with #4966 design

## Impact Analysis
- **Files touched by this audit**: 
  - ✅ `references/sub-skills/common/agent-lifecycle.md` — accurate
  - ✅ `references/sub-skills/common/self-restart.md` — accurate  
  - ✅ `references/sub-skills/common/cycle-runner.md` — accurate
  - ❌ `references/docs/harness-lifecycle-upgrade.md` — one critical inaccuracy
  - ✅ `tests/test_harness.py` — good coverage, minor gaps
  - ✅ `tests/test_cycle_post.py` — good coverage, exit-code-42 gap
  - ⚠️ `tests/test_start_team.py` — missing `cmd_boot` test
  - ⚠️ `tests/test_thin_launcher.py` — very thin, missing `main()` test
- **Stale files discovered (NOT in review list)**:
  - ❌ `references/agent-instructions.md` lines 803–863 — old sub-skills inlined (wrapper/.stop-after-cycle/.health/.pid)
  - ❌ `references/sub-skills/common/boot-remote-agents.md` line 16 — "wrapper scripts"
  - ❌ `references/sub-skills/roles/pm/health-check.md` lines 12, 19 — ".health" and "wrapper"
  - ❌ `references/sub-skills/roles/pm/pipeline-sentinel.md` line 121 — "Boot wrapper"
  - ⚠️ `references/scripts/cycle_pre.py` line 506 — stale comment about wrapper/stop-after-cycle
- **Behavior changes**: wrapper → harness owns lifecycle; sentinels → API intents; `.health` → PID checks; `.stop-after-cycle` → `GET /agents/{role}` intent query; exit code 42 signals harness to respawn
- **Dependencies**: `compose.py` must be re-run after sub-skill updates to regenerate `agent-instructions.md`

## Side Effects
- **Risk 1**: Agents see stale wrapper-era instructions — Severity: **H** — Mitigation: Must regenerate `agent-instructions.md` via `compose.py deploy-all` after fixing all stale sub-skill sources. Without this, agents will try to read `.stop-after-cycle` and `.health` files that no longer exist, and won't know to query harness API.
- **Risk 2**: Upgrade doc tells users to delete `.claude-pid` and `.booting` — Severity: **M** — Mitigation: Fix upgrade doc to NOT delete these. `.claude-pid` is the primary PID communication channel between thin launcher and harness. `.booting` is still used by `boot_remote.py` for boot slot acquisition (lines 222-253).
- **Risk 3**: PM sub-skills (`health-check.md`, `boot-remote-agents.md`, `pipeline-sentinel.md`) tell PM to read `.health` files and reference "wrapper" — Severity: **M** — Mitigation: These are PM-only sub-skills, but PM will get incorrect guidance about agent monitoring.

## Edge Cases
- **Harness API unreachable at cycle end**: `_query_harness_intent` returns `None`, `_do_stop_after_cycle_check` falls back to context pressure only — tested, correct (test_cycle_post.py:371-376)
- **No context_pressure data in cycle-output.json**: Falls through, tries cycle-input.json, returns False — tested (test_cycle_post.py:378-383)
- **Legacy restart_needed still in cycle-output.json**: `_do_restart_sentinel` still writes `.restart` (deprecated path, kept for one-version backward compat) — tested (test_cycle_post.py:385-391)
- **Harness crash while agents running**: `.harness-state.json` persists intents/PIDs; on restart, `load_state()` restores state, health poll re-detects agent aliveness — tested (test_harness.py:76-133)
- **Intent=stopping agent dies**: Intent transitions to "stopped", no reboot — tested (test_harness.py:500-524)
- **Intent=restarting agent comes back alive**: Intent transitions back to "running" — tested (test_harness.py:526-562)
- **Ctrl+C in thin launcher terminal**: KeyboardInterrupt captured, waits 30s for claude to exit, then kills — NOT tested
- **claude not on PATH**: thin_launcher returns exit code 1 — NOT tested
- **Port file from parent directory (clone isolation)**: `_discover_harness_port` walks up 5 levels — only tested for direct port file, NOT parent-dir walk (test_cycle_post.py:397-414)

## Integration Risks
- **compose.py regeneration**: If any agent CLAUDE.md is composed before all stale sub-skills are fixed, agents will receive mixed messages (some harness-aware, some wrapper-era). The upgrade doc's Step 5 (`compose.py deploy-all`) is correct but must only be run after all source sub-skills are updated.
- **boot_remote.py dual-path**: `_find_boot_script` (line 370-402) still has legacy wrapper fallback. If a clone lacks `thin_launcher.py`, it falls back to wrapper scripts. This is documented as backward compat but means the wrapper era isn't fully dead — the `_needs_boot` function still reads `.health` files, `.pid` files, and `.stop` sentinels (lines 302-353). This is intentional backward compat, not a bug.
- **`.stop` sentinel still used**: Both harness (`_has_stop_sentinel` in update_health, line 207) and boot_remote (`_needs_boot`, line 312) still check `.stop` sentinels. The upgrade doc says to delete `.stop` — but `start_team.py` still writes `.stop` as fallback when harness is unreachable (line 172). This creates confusion: is `.stop` dead or alive? The answer: it's a fallback mechanism.

## Upgrade & Migration
- **New config values**: `harness-enabled`, `harness-port` (in config.md, via `config.py`) — documented in upgrade doc
- **New files**: `references/scripts/harness.py`, `references/scripts/thin_launcher.py`, `.squidsquad/.harness-state.json`, `.squidsquad/.harness-port`
- **Template changes**: `agent-lifecycle.md`, `self-restart.md`, `cycle-runner.md` updated; `boot-remote-agents.md`, `health-check.md`, `pipeline-sentinel.md` NOT updated
- **Upgrade steps**: Steps 1-6 in harness-lifecycle-upgrade.md are correct EXCEPT:
  - **Step 3 is wrong**: Do NOT delete `.claude-pid` (still written by thin launcher, harness reads it as PID fallback at harness.py line 176). Do NOT delete `.booting` (still written by boot_remote.py for boot slot acquisition at line 240). Do NOT delete `.stop` if it's the fallback mechanism (still checked at harness.py line 207, boot_remote.py line 312).
  - **Step 4 is correct**: Wrapper scripts should be deleted.
- **Graceful degradation**: If harness not running, `start_team.py --stop` falls back to `.stop` sentinel (start_team.py line 172). If thin launcher not present, boot_remote falls back to legacy wrappers (boot_remote.py lines 385-402). If harness API unreachable at cycle end, agent continues running (cycle_post.py line 494).

## Open Questions
- **Q1**: Should `.stop` sentinel be fully deprecated or kept as fallback? — **Why**: Both harness and boot_remote still check it. If the upgrade doc tells users to delete it, but code still relies on it as fallback, there's a conflict. The code behavior is correct (fallback is good), but the upgrade doc is wrong.
- **Q2**: Should `agent-instructions.md` be regenerated as part of this PR or as a separate deployment step? — **Why**: It's stale right now but is the compose output. If regenerate now, agents get correct instructions immediately. But if sub-skills are still being tweaked, regeneration should wait until all source files are correct.
- **Q3**: Are the PM sub-skills (`health-check.md`, `boot-remote-agents.md`, `pipeline-sentinel.md`) in scope for #4966 or a separate task? — **Why**: They're actively wrong but weren't in the review list. PM will get incorrect guidance.

## Recommendation
**FAIL — Needs rethinking on some items, but fixable.**

The new sub-skill files (agent-lifecycle.md, self-restart.md, cycle-runner.md) are accurate. The test suite has good coverage with manageable gaps. However, there are CRITICAL blockers:

1. `agent-instructions.md` is stale (old wrapper-era content) — this is what agents actually read
2. 4 source sub-skill files still reference wrapper/health patterns
3. Upgrade doc instructs deletion of files still in active use

These are all fixable — update the stale sub-skills, regenerate agent-instructions.md, fix the upgrade doc's Step 3. But they must be fixed before this can pass.

---

## CRITICAL Issues (must fix)

### C1: `references/agent-instructions.md` contains pre-#4966 wrapper-era sub-skills
- **Lines 803–863**: Old `self-restart` and `agent-lifecycle` sub-skills reference `.stop-after-cycle` sentinel (line 812, 817, 832, 859), wrapper scripts (line 813, 820, 828, 833), `.health` heartbeat files (line 835, 862), `.pid` singleton lock (line 831, 861).
- **Impact**: Agents composed from this file will try to read files that no longer exist and won't know to query harness API for intent. All agent behavior will be wrong.
- **Fix**: Regenerate via `compose.py deploy-all` AFTER fixing all stale sub-skill source files (C2–C4 below).

### C2: `references/sub-skills/common/boot-remote-agents.md` line 16 — stale "wrapper scripts" reference
- **Current**: "Agent lifecycle is managed by `start_team.py` and the wrapper scripts."
- **Should be**: "Agent lifecycle is managed by the harness (`harness.py`) via REST API."
- **Impact**: PM agents get incorrect lifecycle guidance.

### C3: `references/sub-skills/roles/pm/health-check.md` lines 12, 19 — stale ".health" and "wrapper" references
- **Line 12**: "The script reads each agent's heartbeat file (`.squidsquad/<role>/.health`) — the wrapper writes the current epoch every 5 seconds."
- **Line 19**: "agent lifecycle is managed by `start_team.py` and the wrapper scripts."
- **Impact**: PM agents try to read `.health` files that no longer exist post-#4966.

### C4: `references/sub-skills/roles/pm/pipeline-sentinel.md` line 121 — "Boot wrapper" reference
- **Current**: "Boot wrapper may need investigation."
- **Should be**: "Harness may need investigation."

### C5: Upgrade doc Step 3 incorrectly tells users to delete `.claude-pid` and `.booting`
- **File**: `references/docs/harness-lifecycle-upgrade.md` lines 33, 36
- **Problem**: `.claude-pid` is still written by `thin_launcher.py` (line 75) and read by `harness.py` as PID fallback (line 176). `.booting` is still written by `boot_remote.py` for boot slot acquisition (line 240).
- **Fix**: Remove `.claude-pid` and `.booting` from the deletion list. Only `.health`, `.pid`, `.restart`, `.stop-after-cycle` should be deleted. `.stop` should be noted as "optional — still used as fallback."

## NON-CRITICAL Issues (should fix)

### N1: `references/scripts/cycle_pre.py` line 506 — stale code comment
- **Current**: `# Wrapper handles all respawning via .stop-after-cycle sentinel.`
- **Should be**: `# Harness handles respawning via intent API + exit code 42 (#4966).`

### N2: No test for exit code 42 from `cycle_post.main()`
- **File**: `tests/test_cycle_post.py`
- **Gap**: `_do_stop_after_cycle_check` is unit-tested, but `main()` returning 42 when `stop_for_restart=True` is never tested end-to-end. The harness relies on this exit code to trigger respawn.
- **Fix**: Add a test that calls `cycle_post.main()` with a full cycle-output.json containing exceeded context pressure, and asserts return code 42.

### N3: `tests/test_thin_launcher.py` — no test for `thin_launcher.main()`
- **Gap**: Only tests `_write_pid` and `_clear_pid` helpers. `main()` is never called.
- **Missing tests**: exit code 42 passthrough, `claude` not on PATH, KeyboardInterrupt handling, `SQUIDSQUAD_ROLE` env var propagation.
- **Fix**: Add tests for main() with mocked subprocess.Popen.

### N4: `tests/test_start_team.py` — no test for `cmd_boot`
- **Gap**: `cmd_stop`, `cmd_reboot`, sentinel ops, and CLI parsing are tested. `cmd_boot` — the default action when no `--stop`/`--reboot` flag — is not tested.
- **Fix**: Add test for `cmd_boot` calling `boot_remote.boot_agent` for each role.

### N5: No test for harness Ctrl+C escalation
- **File**: `tests/test_harness.py`
- **Gap**: `CtrlCHandler` (harness.py lines 795-856) with its three-stage escalation is untested.
- **Fix**: Add tests for: 1st Ctrl+C sets all agents intent=stopping, 2nd Ctrl+C within 5s warns, 3rd Ctrl+C calls `os._exit(1)`.

### N6: `tests/test_cycle_post.py` — no test for parent-dir port discovery walk
- **Gap**: `_discover_harness_port` (cycle_post.py lines 446-475) has a parent-dir walk for clone isolation (lines 460-473). Only the direct `.harness-port` path is tested (lines 397-414).
- **Fix**: Add test with `.harness-port` in a parent directory.

### N7: Upgrade doc Step 3 lists `.stop` as "no longer written"
- **File**: `references/docs/harness-lifecycle-upgrade.md` line 35
- **Problem**: `.stop` IS still written by `start_team.py` as fallback (line 172) and checked by both harness (line 207) and boot_remote (line 312).
- **Fix**: Clarify that `.stop` is kept as fallback mechanism and should NOT be bulk-deleted.

## PASS/FAIL Verdict

**FAIL** — 5 CRITICAL issues must be resolved before this is shippable:

| # | Issue | Location |
|---|-------|----------|
| C1 | Stale pre-#4966 sub-skills in agent-instructions.md | `references/agent-instructions.md:803-863` |
| C2 | "wrapper scripts" reference | `references/sub-skills/common/boot-remote-agents.md:16` |
| C3 | ".health" and "wrapper" references | `references/sub-skills/roles/pm/health-check.md:12,19` |
| C4 | "Boot wrapper" reference | `references/sub-skills/roles/pm/pipeline-sentinel.md:121` |
| C5 | Incorrect sentinel deletion instructions | `references/docs/harness-lifecycle-upgrade.md:33,36` |

The new sub-skill content (agent-lifecycle.md, self-restart.md, cycle-runner.md) and test architecture are solid — the failures are in **stale content that was missed during the update**. All are straightforward text fixes.

## Vault Candidates
- **Type**: learning — "compose.py output is a derived artifact; always regenerate after sub-skill source changes" — **Why**: The agent-instructions.md staleness would have been caught if compose had been re-run. This is a process gap worth remembering.
- **Type**: learning — "upgrade docs must be verified against current code, not design intent" — **Why**: The .claude-pid/.booting deletion instruction was written from design intent ("no more sentinel files") rather than verified against actual code behavior. A code grep would have caught it.
- **Type**: pattern — "sentinel files: distinguish 'still-written' from 'no-longer-written' during migration" — **Why**: The .claude-pid/.booting/.stop sentinels form a fourth category: "still written by new system." The upgrade doc treats all sentinels as equally deprecated, which is wrong. A migration sentinel inventory checklist pattern would prevent this.
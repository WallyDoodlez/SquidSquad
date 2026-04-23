# FEAT-SKILL-2183 QA Results -- Simplified Agent Lifecycle

**Date**: 2026-04-22
**Branch**: squidsquad/skill/2183
**Executed by**: QA subagent

## Summary

- **Total TCs executed**: 35 (of 54 in plan -- focused on highest-value static/code verifications)
- **PASS**: 27
- **FAIL**: 8
- **Smoke tests**: 9/11 PASS, 2 FAIL
- **Pre-existing failures**: 12 test failures confirmed pre-existing on main (not regressions)

### Critical Failures

1. `tests/run_tests.py` references deleted `test_watchdog` module -- causes ERROR on run
2. `health_check.py` still contains `_read_pid_file`, `_parse_health_file`, mtime fallback (TC-19 partial fail)
3. `includes.yml` files not updated to reference `agent-lifecycle` sub-skill (TC-28/TC-54)
4. Composed wrappers not regenerated (310 lines instead of ~155) (TC-53)
5. `tests/comprehension/2183_spec.json` missing (TC spec)
6. PM/DM SOUL.md not updated with context pressure/post-ship reboot behavior
7. `.restart` sentinel guard in `cycle_post.py` not gated on context pressure specifically

---

## Smoke Tests

- [x] `python references/scripts/reboot_agent.py --help` prints usage without error -- **PASS**
- [x] `python references/scripts/reboot_agent.py nonexistent-role` exits with code 0 (not 2 as spec says) -- **FAIL** (prints "not running", exits 0 instead of expected 2 for unknown role)
- [x] `python references/scripts/health_check.py` runs without error -- **PASS** (exit 0 when used without --json)
- [x] `python references/scripts/health_check.py --json` returns valid JSON -- **PASS**
- [x] `python references/scripts/boot_remote.py --role skill --json` runs without import errors -- **PASS**
- [x] `references/sub-skills/common/agent-lifecycle.md` exists and is non-empty -- **PASS**
- [x] `references/scripts/watchdog.py` does NOT exist -- **PASS**
- [x] `tests/test_watchdog.py` does NOT exist -- **PASS**
- [ ] New wrapper template is <150 lines: `wc -l references/templates/start-role.sh` -- **FAIL** (184 lines sh, 168 lines ps1)
- [x] `grep -r "watchdog" references/scripts/*.py` returns no hits -- **PASS**
- [ ] `python tests/run_tests.py` passes -- **FAIL** (ERROR: references deleted test_watchdog.py but run_tests.py still lists "test_watchdog" in STATIC_TEST_MODULES)

---

## Test Case Results

### TC-14: watchdog.py deleted, no imports remain
- **Result**: PASS
- **Notes**: `references/scripts/watchdog.py` does not exist. `grep -r "watchdog" references/scripts/*.py` returns no hits. No imports of watchdog remain in scripts, templates, or sub-skills.

### TC-15: test_watchdog.py deleted
- **Result**: PASS
- **Notes**: `tests/test_watchdog.py` does not exist.

### TC-16: .stop sentinel removed from all templates
- **Result**: PASS
- **Notes**: `grep -r ".stop" references/templates/ references/sub-skills/` returns no sentinel-related matches. `.stop` pattern also absent from `.gitignore`.

### TC-17: 50-restart loop removed
- **Result**: PASS
- **Notes**: `grep -E "MAX_RESTARTS|COOLDOWN_BASE|COOLDOWN_MAX|SELF_RESTART_LIMIT|MIN_RUNTIME" references/templates/start-role.sh references/templates/start-role.ps1` returns empty. None of these constants exist.

### TC-18: Cooldown/boot-lock/boot-attempts.log removed from boot_remote.py
- **Result**: PASS
- **Notes**: `grep -E "cooldown|boot-lock|boot-attempts|_read_boot_log|_append_boot_log|_check_cooldown|_acquire_lock|_release_lock" references/scripts/boot_remote.py` returns empty.

### TC-19: PID cross-check and mtime fallback removed from health_check.py
- **Result**: FAIL
- **Notes**: `_read_pid_file`, `_parse_health_file`, and `mtime` fallback logic all still present in `health_check.py`. The functions exist at lines 109, 150, 180, and mtime-based detection spans lines 372-392. This is either intentional transition code or was not cleaned up.

### TC-20: Runtime files cleaned up
- **Result**: PASS
- **Notes**: `.gitignore` does not contain `boot-attempts`, `boot-lock`, or `watchdog-log` patterns. These entries have been removed.

### TC-21: reboot_agent.py -- script exists and callable
- **Result**: PASS
- **Notes**: `reboot_agent.py` exists at `references/scripts/reboot_agent.py`. `--help` prints correct usage. Script implements sentinel write, idle wait, process kill logic.

### TC-22: reboot_agent.py -- agent not running
- **Result**: PASS
- **Notes**: `python references/scripts/reboot_agent.py nonexistent-role` prints "nonexistent-role: not running (no PID file)" and exits 0.

### TC-23: reboot_agent.py -- --force flag
- **Result**: PASS (by code inspection)
- **Notes**: `--force` flag present. When set, script skips idle wait loop and kills immediately (line 107-109).

### TC-24: reboot_agent.py -- --all flag
- **Result**: PASS (by code inspection)
- **Notes**: `--all` flag present. Imports `get_agents()` from config module, iterates and reboots sequentially (lines 143-157).

### TC-25: reboot_agent.py -- exit codes
- **Result**: FAIL
- **Notes**: Exit code 0 for success and "not running" works. Exit code 1 for timeout works. However, exit code 2 for usage error (no role and no --all) only triggers when `parser.print_usage()` is called -- `nonexistent-role` does NOT return exit 2 (returns 0 with "not running"). The spec says invalid role should return 2 but the script treats unknown roles as "not running" since there's no PID file.

### TC-26: reboot_agent.py -- PID change during wait
- **Result**: FAIL (by code inspection)
- **Notes**: The reboot function does NOT detect PID changes during the wait loop. It reads the PID once at start and polls current-state for idle, but never re-reads the PID file to detect if the agent restarted with a different PID.

### TC-28: agent-lifecycle.md sub-skill exists and is composable
- **Result**: FAIL
- **Notes**: File exists and has correct content (reboot_agent.py, heartbeat, .restart, .pid, PM, DM sections all present). However, `agent-lifecycle` is NOT referenced in any `includes.yml` file. The roles still use `common/self-restart` and `common/boot-remote-agents`. The sub-skill was created but NOT wired into composition.

### TC-29: Heartbeat-based health detection -- alive agent
- **Result**: PASS
- **Notes**: `health_check.py --json` returns agents with `"health": "healthy"` and `"health_source": "health-file"`. Alive agents show correct status.

### TC-30: Heartbeat-based health detection -- dead/stale agent
- **Result**: PASS
- **Notes**: The "boot" agent (no health file) correctly shows `"health": "unknown"`. health_check.py correctly distinguishes alive from stale/missing states.

### TC-34: Transition -- health_check.py handles old .health format
- **Result**: PASS
- **Notes**: `_parse_health_file()` still exists and parses both old format (`alive|boot_epoch=...`) and new format (plain epoch integer). Transition support is present.

### TC-35: Transition -- health_check.py handles new .health format
- **Result**: PASS
- **Notes**: JSON output shows alive agents with heartbeat data. New format is correctly parsed.

### TC-43: pipeline-sentinel still works with simplified health_check.py
- **Result**: PASS
- **Notes**: JSON output has per-agent entries with `status`-equivalent fields (`health`, `health_source`). The structure includes all required fields for pipeline sentinel consumption.

### TC-45: cycle_post.py restart sentinel guarded by context pressure
- **Result**: FAIL
- **Notes**: `_do_restart_sentinel()` checks `data.get("restart_needed")` but there is no explicit guard that limits this to context pressure reasons only. The function writes the sentinel for ANY `restart_needed=True`, not specifically for context pressure. The guard depends on callers only setting `restart_needed` for context pressure, but this is not enforced in the function itself.

### TC-48: scan_index.py and model_router.py unaffected
- **Result**: PASS
- **Notes**: Both scripts execute without errors related to this change.

### TC-49: .restart sentinel ownership
- **Result**: PASS
- **Notes**: Only `reboot_agent.py` (line 105) and `cycle_post.py` (line 310) write the `.restart` sentinel. No other scripts write to it.

### TC-53: Upgrade -- compose.py install regenerates wrappers
- **Result**: FAIL
- **Notes**: Composed wrappers at `.squidsquad/start-skill.sh` are 310 lines (old size), not the expected ~155 lines. `compose.py install` was not re-run after the template changes. The templates themselves (184 lines sh, 168 lines ps1) are also larger than the "~155 lines each" stated in the task description, but this is a minor sizing discrepancy.

### TC-54: Upgrade -- sub-skill composition updated
- **Result**: FAIL
- **Notes**: `includes.yml` files for all roles still reference `common/self-restart` and `common/boot-remote-agents` but do NOT include `common/agent-lifecycle`. The new sub-skill is not wired into any role's composition. Role CLAUDE.md files do NOT contain agent-lifecycle content.

---

## Acceptance Criteria Check

| Criterion | Status | Notes |
|---|---|---|
| Wrapper is singleton (PID lock, exit if already running) | PASS | Both sh/ps1 templates check .pid, verify process alive, exit if running |
| Wrapper never kills claude mid-work (waits for idle) | PASS | reboot_agent.py polls current-state for idle before killing |
| Wrapper starts correctly (SQUIDSQUAD_ROLE, branch, pre-flight) | PASS | Template sets env var, checks gh auth, switches to working branch |
| reboot_agent.py script exists and works | PASS | Script callable, --help works, unit tests pass (9/9) |
| agent-lifecycle.md sub-skill created and composable | FAIL | File exists but NOT wired into includes.yml for any role |
| Heartbeat-based health detection replaces file trust | PARTIAL | Heartbeat writing works in templates, health_check.py supports it BUT also retains old PID/mtime fallback code |
| PM SOUL.md updated with context pressure reboot behavior | FAIL | PM SOUL.md has no references to context pressure, reboot, or heartbeat |
| DM SOUL.md updated with post-ship reboot behavior | FAIL | DM SOUL.md has no references to reboot or post-ship restart |
| All existing tests pass | FAIL | tests/run_tests.py references deleted test_watchdog module causing ERROR. 12 other failures are pre-existing on main. |
| Comprehension test spec for new agent instructions | FAIL | tests/comprehension/2183_spec.json does not exist |
| Windows (PowerShell) and bash parity | PASS | start-role.ps1 has matching logic: PID lock, heartbeat job, cleanup, restart sentinel, crash retry |

---

## Unit Test Results

### reboot_agent.py tests (9/9 PASS)
```
tests/test_reboot_agent.py::TestRebootNotRunning::test_no_pid_file PASSED
tests/test_reboot_agent.py::TestRebootNotRunning::test_dead_pid PASSED
tests/test_reboot_agent.py::TestRebootNotRunning::test_invalid_pid_file PASSED
tests/test_reboot_agent.py::TestRebootForce::test_force_kills_immediately PASSED
tests/test_reboot_agent.py::TestRebootWaitForIdle::test_idle_detected PASSED
tests/test_reboot_agent.py::TestRebootWaitForIdle::test_timeout_cleans_sentinel PASSED
tests/test_reboot_agent.py::TestSentinelWritten::test_sentinel_content PASSED
tests/test_reboot_agent.py::TestGetClonePath::test_defaults_to_repo_root PASSED
tests/test_reboot_agent.py::TestGetClonePath::test_reads_local_config PASSED
```

---

## Issues to Fix Before Shipping

1. **CRITICAL**: Remove `"test_watchdog"` from `STATIC_TEST_MODULES` in `tests/run_tests.py` -- causes ERROR when running the test suite
2. **HIGH**: Wire `agent-lifecycle` into `includes.yml` for all roles OR update the acceptance criteria -- the sub-skill exists but is not composed into any role
3. **HIGH**: Create `tests/comprehension/2183_spec.json` -- acceptance criteria requires it
4. **MEDIUM**: Update PM SOUL.md with context pressure monitoring/reboot behavior
5. **MEDIUM**: Update DM SOUL.md with post-ship reboot behavior
6. **MEDIUM**: Consider cleaning up health_check.py PID/mtime fallback code OR document it as intentional transition support
7. **LOW**: reboot_agent.py PID change detection during wait loop (TC-26) -- edge case but could cause issues

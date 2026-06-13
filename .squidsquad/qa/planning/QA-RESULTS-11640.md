# QA-RESULTS-11640 — boot_remote._get_clone_path must FAIL, not fall back to REPO_ROOT

**Verifier**: verifier-lead (qa)
**Date**: 2026-06-13
**PR**: #11709 (squidsquad/task/11640 → main)
**Branch verified**: squidsquad/task/11640 @ cab96789b
**Verdict**: **PASS** (defensive half of #11600; the qa→verifier clone-registration half stays on #11600)

## AC Walk

### AC-1: _get_clone_path('unregistered-role') raises
**PASS.** boot_remote.py:182-190 — `if role not in local: raise CloneResolutionError(...)`.
Uses `local[role]` (not `.get(role, REPO_ROOT)`). Test: test_unregistered_role_raises.

### AC-2: registered-but-nonexistent path raises
**PASS.** boot_remote.py:191-198 — `if not Path(path).exists(): raise CloneResolutionError(...)`.
Test: test_registered_nonexistent_path_raises.

### AC-3: every spawn path refuses + spawns zero terminals (no REPO_ROOT boot)
**PASS.** Single gate at boot_agent (boot_remote.py:565): `_needs_boot` → `_get_clone_path`
raises → caught → result{action:error, success:False, message:"clone resolution failed —
refusing to spawn"}, returns BEFORE orphan sweep / sentinel / terminal spawn. Covers manual
boot, harness auto-reboot (#4949), and POST /agents/{role}/start (all route through boot_agent).
Harness also surfaces refusal at harness.py:482 (auto-reboot) and skips at 1617 (stop_all/shutdown).
Test: TestBootAgentCloneResolutionRefusal::test_unregistered_role_refuses_spawn asserts
success=False, action=error, AND `_write_booting_sentinel.assert_not_called()` +
`_spawn_terminal.assert_not_called()` (the zero-spawn guarantee). + test_dry_run_also_refuses.

### AC-4: pm/skill/dm continue to resolve (explicit repo-root registration valid)
**PASS.** An explicit `pm: .` registration resolves normally; only an UNregistered role
defaulting to repo-root was the bug. Tests: test_explicit_repo_root_registration_resolves,
test_registered_existing_path_resolves, test_returns_str_not_path (JSON-serializable for AgentState).

### Stale test handled correctly (not papered over)
skill UPDATED the pre-existing test_get_clone_path_falls_back_to_repo_root (feat_1496, asserted
the OLD REPO_ROOT fallback) to assert the new CloneResolutionError raise (commit cab96789b) —
correct: the old behavior is the bug being reversed.

## Test Execution
- `pytest tests/test_boot_remote.py tests/test_harness.py` → **237 passed, 1 skipped**, EXIT=0.
- TestGetClonePath (6) + TestBootAgentCloneResolutionRefusal (2) all green.
- `python tests/run_tests.py static` → EXIT=0, 2264 passed / 0 failed.
- skill full suite green; DS review NO_FINDINGS (8 spawn paths verified refuse safely).

## Verdict
**PASS → pending-ship.** The exact #11600 incident (qa silently booting into PM's clone) is now
a loud refusal + zero spawn, regression-tested. DM ships PR #11709.

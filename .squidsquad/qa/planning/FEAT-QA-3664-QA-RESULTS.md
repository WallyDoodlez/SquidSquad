# FEAT-QA-3664 QA Results — Move iterations and diagnostics to state branch

**Date**: 2026-04-27
**Branch**: squidsquad/skill/3664
**Tested by**: qa-lead (subagent)
**Test file**: `.squidsquad/qa/planning/FEAT-QA-3664-tests.py`

---

## Summary Table

| TC  | Title                                              | Result          | Notes |
|-----|----------------------------------------------------|-----------------|-------|
| TC-1 | Path helper resolves state files to worktree      | PASS            | 7 assertions, all green |
| TC-2 | cycle_post.py writes state files to state branch  | PASS            | working-state routed to worktree; state commit called when worktree present |
| TC-3 | cycle_pre.py reads state files from state worktree | FAIL            | Bug: `_get_cycle_number` passes `"skill/iterations"` (no trailing slash) to `is_state_file()`, which requires `"iterations/"` — so dir never routes to state worktree |
| TC-4 | diagnostics writes to state worktree              | FAIL            | Bug: `diagnostics.py` calls `_state_path("diagnostics")` at module load (no trailing slash); `is_state_file("diagnostics")` returns False — dir stays on main |
| TC-5 | scan-history.md writes to state worktree          | PASS            | write_file/read_file round-trip correct |
| TC-6 | scan_index.py rebuild finds files in state worktree | PASS           | Both search dirs checked; state worktree preferred; dedup works |
| TC-7 | .backlog-cache is gitignored                      | PASS            | `.squidsquad/.backlog-cache` and `.squidsquad/.backlog-cache.tmp` both in .gitignore |
| TC-8 | Migration copies all state files to state branch  | HUMAN-REQUIRED  | Needs real git repo with state branch |
| TC-9 | Migration auto-deletes state files from main      | HUMAN-REQUIRED  | Requires TC-8 completed |
| TC-10 | Graceful degradation without worktree            | PASS            | state_path() falls back cleanly; no crash |
| TC-11 | Main branch commits no longer contain state files | HUMAN-REQUIRED  | Needs live cycle run on migrated repo |
| TC-12 | Concurrent agent writes to state branch          | HUMAN-REQUIRED  | Needs two running agents |
| TC-13 | state_bus.init() is idempotent                   | PASS            | No duplicate worktree, no extra git commands, returns 0 |

**Overall**: 2 FAIL, 7 PASS, 4 HUMAN-REQUIRED

---

## Bugs Found

### Bug 1 — TC-3: `_get_cycle_number` never reads from state worktree

**File**: `references/scripts/cycle_pre.py` (and same issue in `cycle.py`)
**Function**: `_get_cycle_number`, `log_iteration`, `cleanup_iterations`

**Root cause**: These functions call `_state_path(f"{role}/iterations")` — without a trailing slash. `is_state_file()` matches directory patterns only when they end with `/`. The check is:
```python
if f"/{pattern}" in f"/{rel}" or rel.startswith(pattern):
    return True
```
For `pattern = "iterations/"` and `rel = "skill/iterations"`:
- `/iterations/` is NOT in `/skill/iterations` (no trailing slash)
- `"skill/iterations"`.startswith(`"iterations/"`) is False

So `is_state_file("skill/iterations")` returns `False`, and all iteration file operations fall back to `.squidsquad/` instead of `.squidsquad-state/`.

**Impact**: Cycle numbers will be read from (and iteration logs written to) the main branch instead of the state branch — defeating the entire purpose of TC-3 routing.

**Fix options**:
1. Change call sites to pass a trailing slash: `_state_path(f"{role}/iterations/")`
2. OR update `is_state_file()` to also match paths that equal the pattern base without trailing slash (add `rel == pattern.rstrip("/")` check).

### Bug 2 — TC-4: `diagnostics.py` DIAGNOSTICS_DIR not in state worktree

**File**: `references/scripts/diagnostics.py`
**Line**: `DIAGNOSTICS_DIR = _state_path("diagnostics")` (module-level)

**Root cause**: Same trailing-slash issue. `state_path("diagnostics")` calls `is_state_file("diagnostics")` which returns `False` because the pattern `"diagnostics/"` requires a trailing slash. So `DIAGNOSTICS_DIR` is set to `.squidsquad/diagnostics/` at module load, not `.squidsquad-state/diagnostics/`.

Same root cause affects `model_router.py`: `DIAGNOSTICS_DIR = _state_path("diagnostics")`.

**Fix**: Change to `_state_path("diagnostics/")` (with trailing slash) in both `diagnostics.py` and `model_router.py`.

---

## Dev Tests (`tests/test_state_bus.py`)

All 29 dev-provided tests pass:

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.0.2, pluggy-1.6.0
collected 29 items

tests/test_state_bus.py::TestReadBranchConfig::test_reads_from_config PASSED
tests/test_state_bus.py::TestReadBranchConfig::test_defaults_when_missing PASSED
tests/test_state_bus.py::TestReadBranchConfig::test_defaults_when_no_section PASSED
tests/test_state_bus.py::TestWorktreeExists::test_true_when_git_present PASSED
tests/test_state_bus.py::TestWorktreeExists::test_false_when_missing PASSED
tests/test_state_bus.py::TestWorktreeExists::test_false_when_no_git PASSED
tests/test_state_bus.py::TestReadFile::test_reads_existing_file PASSED
tests/test_state_bus.py::TestReadFile::test_returns_none_for_missing PASSED
tests/test_state_bus.py::TestReadFile::test_returns_none_when_no_worktree PASSED
tests/test_state_bus.py::TestWriteFile::test_writes_file PASSED
tests/test_state_bus.py::TestWriteFile::test_creates_subdirs PASSED
tests/test_state_bus.py::TestWriteFile::test_fails_when_no_worktree PASSED
tests/test_state_bus.py::TestStatus::test_outputs_json PASSED
tests/test_state_bus.py::TestInitBranchRecovery::test_captures_original_branch PASSED
tests/test_state_bus.py::TestInitBranchRecovery::test_restores_branch_on_failure PASSED
tests/test_state_bus.py::TestInitBranchRecovery::test_no_hardcoded_main_fallback PASSED
tests/test_state_bus.py::TestIsStateFile::test_iterations_is_state PASSED
tests/test_state_bus.py::TestIsStateFile::test_working_state_is_state PASSED
tests/test_state_bus.py::TestIsStateFile::test_scan_history_is_state PASSED
tests/test_state_bus.py::TestIsStateFile::test_diagnostics_is_state PASSED
tests/test_state_bus.py::TestIsStateFile::test_config_is_not_state PASSED
tests/test_state_bus.py::TestIsStateFile::test_claude_md_is_not_state PASSED
tests/test_state_bus.py::TestIsStateFile::test_vault_is_not_state PASSED
tests/test_state_bus.py::TestIsStateFile::test_planning_is_not_state PASSED
tests/test_state_bus.py::TestStatePath::test_state_file_with_worktree PASSED
tests/test_state_bus.py::TestStatePath::test_non_state_file_stays_on_main PASSED
tests/test_state_bus.py::TestStatePath::test_state_file_without_worktree_falls_back PASSED
tests/test_state_bus.py::TestCLI::test_help PASSED
tests/test_state_bus.py::TestCLI::test_unknown_command PASSED

============================== 29 passed in 0.13s ==============================
```

---

## QA Tests (`FEAT-QA-3664-tests.py`)

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.0.2, pluggy-1.6.0
collected 32 items

TestTC01PathHelper::test_iterations_resolves_to_state_worktree PASSED
TestTC01PathHelper::test_working_state_resolves_to_state_worktree PASSED
TestTC01PathHelper::test_diagnostics_resolves_to_state_worktree PASSED
TestTC01PathHelper::test_scan_history_resolves_to_state_worktree PASSED
TestTC01PathHelper::test_config_md_stays_on_main PASSED
TestTC01PathHelper::test_claude_md_stays_on_main PASSED
TestTC01PathHelper::test_vault_stays_on_main PASSED
TestTC02CyclePost::test_working_state_update_uses_state_path PASSED
TestTC02CyclePost::test_state_commit_called_when_worktree_exists PASSED
TestTC02CyclePost::test_state_commit_not_called_without_worktree PASSED
TestTC03CyclePre::test_read_working_state_uses_state_path PASSED
TestTC03CyclePre::test_get_cycle_number_uses_state_path FAILED
TestTC03CyclePre::test_get_cycle_number_fallback_without_worktree PASSED
TestTC04Diagnostics::test_diagnostics_dir_resolved_via_state_path PASSED (documents bug)
TestTC04Diagnostics::test_log_entry_writes_to_configured_dir PASSED
TestTC05ScanHistory::test_write_and_read_scan_history PASSED
TestTC06ScanIndexRebuild::test_rebuild_searches_state_worktree PASSED
TestTC06ScanIndexRebuild::test_rebuild_prefers_state_worktree_over_main PASSED
TestTC07BacklogCacheGitignored::test_backlog_cache_in_gitignore PASSED
TestTC07BacklogCacheGitignored::test_backlog_cache_tmp_in_gitignore PASSED
test_tc_08_migration_copies_state_files SKIPPED (HUMAN-REQUIRED)
test_tc_09_migration_deletes_from_main SKIPPED (HUMAN-REQUIRED)
TestTC10GracefulDegradation::test_state_path_falls_back_without_worktree PASSED
TestTC10GracefulDegradation::test_cycle_pre_get_cycle_number_fallback PASSED
TestTC10GracefulDegradation::test_cycle_pre_working_state_fallback PASSED
TestTC10GracefulDegradation::test_worktree_missing_does_not_crash_state_bus PASSED
test_tc_11_main_branch_no_state_files SKIPPED (HUMAN-REQUIRED)
test_tc_12_concurrent_agent_writes SKIPPED (HUMAN-REQUIRED)
TestTC13InitIdempotent::test_init_idempotent_when_branch_exists PASSED
TestTC13InitIdempotent::test_init_idempotent_when_worktree_exists PASSED
TestTC13InitIdempotent::test_init_does_not_duplicate_worktree PASSED
TestTC13InitIdempotent::test_init_readme_path_uses_temp_dir PASSED

=================== 1 failed, 23 passed, 4 skipped in 0.22s ===================
```

### TC-3 Failure Detail

```
FAILED TestTC03CyclePre::test_get_cycle_number_uses_state_path

AssertionError: BUG: _get_cycle_number returns 1 instead of 11.
is_state_file('skill/iterations') returns False because the pattern
'iterations/' requires a trailing slash.
Fix: use _state_path('skill/iterations/') or update is_state_file.
assert 1 == 11
```

---

## HUMAN-REQUIRED Test Cases

### TC-8: Migration copies all state files to state branch
**What human must do**:
1. Ensure the `squid-squad` state branch exists (or run `python references/scripts/state_bus.py init` first)
2. Run `python references/scripts/migrate_state_branch.py`
3. Verify: `git show squid-squad:.squidsquad/<role>/iterations/` contains expected iteration files for each agent role
4. Verify: `git show squid-squad:.squidsquad/<role>/working-state.md` exists for each role
5. Verify: `git show squid-squad:.squidsquad/diagnostics/` exists

### TC-9: Migration auto-deletes state files from main
**What human must do** (requires TC-8 complete first):
1. After TC-8, check main branch: `git ls-tree main .squidsquad/pm/iterations/` — should return empty
2. Also check: `git ls-tree main .squidsquad/skill/iterations/` — should return empty
3. Verify no iteration logs, working-state.md, diagnostics/ remain on main

### TC-11: Main branch commits no longer contain state files
**What human must do** (requires full migration + live agent run):
1. Start an agent and let it complete one cycle after migration
2. Run: `git diff --name-only HEAD~1` on main
3. Verify: output contains no paths matching `*/iterations/*`, `working-state.md`, `diagnostics/*`, or `scan-history.md`

### TC-12: Concurrent agent writes to state branch
**What human must do**:
1. Start both skill and pm agents simultaneously on a migrated repo
2. Let both agents complete one full cycle concurrently
3. Run: `git log squid-squad --oneline -20`
4. Verify: both agents' iteration commits appear (look for "skill: cycle N state" and "pm: cycle N state")
5. Verify: no commit conflicts or lost iterations

---

## Verdict

**DO NOT SHIP** in current state. Two implementation bugs block the core feature:

1. **`_get_cycle_number` routing bug** (TC-3 FAIL): iteration directory never routes to state worktree due to missing trailing slash in `is_state_file()` call. Cycle numbers will be wrong (always reset to 1 on state-branch-enabled installs), and iteration logs will be written to the wrong location.

2. **`diagnostics.py` / `model_router.py` routing bug** (TC-4 FAIL): `DIAGNOSTICS_DIR` is resolved to `.squidsquad/diagnostics/` at module load instead of `.squidsquad-state/diagnostics/` due to the same trailing-slash issue. Diagnostic logs stay on main branch.

**Fix required**: In `cycle_pre.py`, `cycle.py`, `diagnostics.py`, and `model_router.py`, change calls from `_state_path(f"{role}/iterations")` to `_state_path(f"{role}/iterations/")` and from `_state_path("diagnostics")` to `_state_path("diagnostics/")`. Alternatively, extend `is_state_file()` to match bare directory names without trailing slash.

The `state_bus.py` module itself (`is_state_file`, `state_path`, `init`, `read_file`, `write_file`) is solid — all 29 dev tests pass.

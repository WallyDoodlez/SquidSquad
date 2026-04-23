# QA Results: #2070 Cycle Runner Script

**Branch**: `squidsquad/skill/2070`
**Date**: 2026-04-22
**Overall**: 4 FAIL, 12 PASS

---

## 1. Smoke Tests

### TC-01: cycle_pre.py pm exits 0 and produces valid JSON
- **Result**: PASS
- **Notes**: Exit code 0. cycle-input.json written. role=pm, cycle_number=465 (positive int), timestamp=2026-04-22T21:02:19 (valid ISO 8601).

### TC-02: cycle_pre.py skill exits 0 and produces valid JSON
- **Result**: PASS
- **Notes**: Exit code 0. cycle-input.json written. role=skill, cycle_number=207, timestamp=2026-04-22T21:02:22.

### TC-03: cycle_pre.py qa exits 0 and produces valid JSON
- **Result**: FAIL
- **Notes**: Crashes with `FileNotFoundError: [WinError 2]` at line 520 in `_build_qa_input`. The config value for `e2e-tests` returns the string `(none)` which passes the truthy check on line 519 (`if e2e_cmd and e2e_cmd.strip()`), then tries to run `(none)` as a shell command. Fix: add a guard like `if e2e_cmd and e2e_cmd.strip() and e2e_cmd.strip() != "(none)"`.

### TC-04: cycle_pre.py dm exits 0 and produces valid JSON
- **Result**: PASS
- **Notes**: Exit code 0. cycle-input.json written. role=dm, cycle_number=138, timestamp=2026-04-22T21:02:40.

### TC-05: cycle-input.json field validation (pm, skill, dm)
- **Result**: PASS
- **Notes**: All three JSON files contain correct `role` field matching argument, `cycle_number` as positive integer, and `timestamp` in valid ISO 8601 format.

### TC-06: cycle-input.json and cycle-output.json in .gitignore
- **Result**: PASS
- **Notes**: `.gitignore` contains both `.squidsquad/*/cycle-input.json` (line 17) and `.squidsquad/*/cycle-output.json` (line 18).

### TC-07: Full test suite passes (python tests/run_tests.py)
- **Result**: PASS (with pre-existing failure)
- **Notes**: 891 tests collected. 2 failures: (1) `test_no_orphan_sub_skills` -- NEW failure caused by this branch, cycle-runner.md not in manifest (see TC-36 notes). (2) `test_dev_agent_has_working_state` -- PRE-EXISTING failure on main (boot agent missing working-state.md). The integration test suite (17 tests) passes fully.

## 2. Unit Tests

### TC-08: pytest test_cycle_pre.py test_cycle_post.py
- **Result**: PASS
- **Notes**: 35 tests, all passed in 0.21s. Covers: working state parsing (5), cycle number (3), context pressure (4), pull (3), config flags (1), skill input builder (2), output validation (6), missing/invalid output (3), status transitions (2), iteration log (2), restart sentinel (2), status bar (2).

## 3. Code Review

### TC-56: cycle_pre.py only reads state, does NOT make workflow decisions
- **Result**: PASS
- **Notes**: Script reads git pull state, context pressure, working state, cycle number, work queue, and config flags. Writes all gathered data to cycle-input.json. Does NOT decide which issue to work on or whether verification passed. QA branch-switching (lines 535-545) is mechanical branch setup for the first verification item, not a workflow decision.

### TC-57: cycle_post.py only executes declared operations, does NOT second-guess agent decisions
- **Result**: PASS
- **Notes**: Script validates cycle-output.json schema, then executes exactly what's declared: status transitions, tracker comments, working state updates, iteration logging, version bumps (DM only), git commits/pushes, restart sentinels. No independent decision-making observed.

## 4. Feature Flag

### TC-36: config.py has cycle-runner mapping
- **Result**: FAIL (partial)
- **Notes**: config.py has the mapping `"cycle-runner": ("Cycle Runner", "Enabled")` at line 68. However, `cycle-runner.md` is not registered in the manifest, causing `test_no_orphan_sub_skills` to fail. The sub-skill file exists but is orphaned from the manifest system.

### TC-38: config.md does NOT have Cycle Runner: yes
- **Result**: PASS
- **Notes**: config.md has no "Cycle Runner" section at all. Feature defaults to off for existing installs, which is correct behavior.

### TC-39: Cycle-runner sub-skill exists in references/sub-skills/
- **Result**: PASS
- **Notes**: `references/sub-skills/common/cycle-runner.md` exists with proper sub-skill markers, feature flag check instructions, and three-phase documentation (pre-cycle, creative, post-cycle).

## 5. Integration Check

### TC-40: git_ops.py pull works independently
- **Result**: PASS
- **Notes**: `python references/scripts/git_ops.py pull` exits 0, outputs "Pulled (stashed and popped)".

### TC-41: tracker.py check-gh works independently
- **Result**: PASS
- **Notes**: `python references/scripts/tracker.py check-gh` exits 0, outputs "OK".

### TC-42: cycle-input/output JSON files don't get committed
- **Result**: PASS
- **Notes**: Both patterns present in .gitignore (lines 17-18). Verified no cycle-input.json or cycle-output.json files appear in git status after smoke tests.

## 6. Acceptance Criteria

### AC-01: cycle_pre.py produces cycle-input.json with queue, context pressure, working state
- **Result**: PASS
- **Notes**: Verified for pm, skill, dm roles. JSON contains `context_pressure` (with used_pct, threshold, exceeded), `working_state` (with task, status, raw_content, steps), and role-specific queue data (work_queue for skill, tracker for pm, bugs for dm). QA role crashes (see TC-03).

### AC-02: cycle_post.py reads cycle-output.json and handles all git/tracker mechanics
- **Result**: PASS
- **Notes**: Code review confirms cycle_post handles: status transitions via tracker.py, tracker comments, working state file updates, iteration logging via cycle.py, version bumps (DM), git commit/push via git_ops.py, restart sentinels, and cleanup. Unit tests (35/35) cover these paths.

### AC-03: Branch switching handled entirely in scripts
- **Result**: PASS
- **Notes**: cycle_pre.py handles branch setup for skill (lines 645-673) and QA (lines 535-545). cycle_post.py handles branch switching for commits (skill code commit on feature branch, state commit on main; QA switches back to main before commit).

### AC-04: Existing test suite still passes
- **Result**: FAIL
- **Notes**: New failure introduced: `test_no_orphan_sub_skills` fails because `cycle-runner.md` is not referenced in the manifest. Pre-existing failure (`test_dev_agent_has_working_state`) is unrelated. The new failure must be fixed before merge.

---

## Blocking Issues (must fix before merge)

1. **QA role crash (TC-03)**: `cycle_pre.py` line 519-520 treats config value `(none)` as a valid command. The guard `if e2e_cmd and e2e_cmd.strip()` does not filter out the placeholder string `(none)`. Add: `and e2e_cmd.strip().lower() != "(none)"`.

2. **Orphan sub-skill (TC-36/AC-04)**: `references/sub-skills/common/cycle-runner.md` is not registered in the manifest, causing `test_no_orphan_sub_skills` to fail. Must add manifest entry or update the test exclusion list.

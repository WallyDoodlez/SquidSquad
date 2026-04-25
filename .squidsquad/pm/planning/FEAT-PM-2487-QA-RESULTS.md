# FEAT-PM-2487 QA Results — Wire Cycle Runner Into Templates

**Executed**: 2026-04-23
**Branch**: main

## Summary Table

| TC | Title | Result |
|----|-------|--------|
| TC-1 | [ROLE] substitution in deployed CLAUDE.md files | PASS |
| TC-2 | Cycle-runner section present in all role templates | PASS (4/4 active roles) |
| TC-3 | cycle_pre.py produces valid cycle-input.json for each role | PASS (4/4 active roles) |
| TC-4 | cycle_post.py processes cycle-output.json for each role | PASS |
| TC-5 | No feature flag gate in deployed templates | PASS |
| TC-6 | PM suppressed cycles via cycle-input.json | PASS |
| TC-7 | QA branch switching handled by cycle_pre/post | HUMAN-REQUIRED |
| TC-8 | Permissive schema — cycle_post warns on missing optional fields | PASS |
| TC-9 | Missing cycle-output.json graceful handling | PASS |
| TC-10 | Existing manual sub-skills not in cycle flow | PASS |
| TC-11 | compose.py deploy-all still works end-to-end | FAIL |
| TC-12 | Rollout — recompose and reboot produces working agents | HUMAN-REQUIRED |

**Overall**: 8 PASS, 1 FAIL, 2 HUMAN-REQUIRED, 1 conditional PASS

---

## Detailed Results

### TC-1: [ROLE] substitution in deployed CLAUDE.md files
- **Result**: PASS
- **Evidence**: Ran `compose.py deploy-all` then checked all 5 roles. Zero occurrences of literal `[ROLE]` in any deployed CLAUDE.md:
  - pm: 0, skill: 0, qa: 0, dm: 0, designer: 0
- **Notes**: designer role has no CLAUDE.md deployed (directory only has `iterations/`), but the check returns 0 for it as well — no literal `[ROLE]` anywhere.

### TC-2: Cycle-runner section present in all role templates
- **Result**: PASS (4/4 active roles)
- **Evidence**: `grep "Cycle Runner"` finds matches in pm, skill, qa, dm. Designer has no deployed CLAUDE.md (only an `iterations/` directory exists under `.squidsquad/designer/`).
- **Notes**: Designer is not a configured active agent in config.md (active agents are boot, qa, skill). The 4 roles with deployed templates all have the cycle-runner section.

### TC-3: cycle_pre.py produces valid cycle-input.json for each role
- **Result**: PASS (4/4 active roles)
- **Evidence**: For pm, skill, qa, dm — all exited 0 and produced valid JSON with required fields: `role`, `cycle_number`, `timestamp`, `pull_result`, `context_pressure`, `working_state`. Role field matches argument in each case.
- **Notes**: `designer` is not a recognized role in cycle_pre.py (exits 1 with "Unknown role"). This is expected — designer is not in the valid roles list.

### TC-4: cycle_post.py processes cycle-output.json for each role
- **Result**: PASS
- **Evidence**: For pm, skill, qa, dm — all exited 0 with minimal cycle-output.json containing required fields. Each wrote an iteration log and committed/pushed successfully.

### TC-5: No feature flag gate in deployed templates
- **Result**: PASS
- **Evidence**: `grep -c "skip this section\|Cycle Runner.*no"` returns 0 for all 4 deployed CLAUDE.md files (pm, skill, qa, dm). Cycle-runner is unconditional.

### TC-6: PM suppressed cycles via cycle-input.json
- **Result**: PASS
- **Evidence**:
  - Without planning phase in working-state.md: `suppressed: False`
  - After setting `**Phase**: researching FEAT-PM-2487` in working-state.md: `suppressed: True`
  - cycle_pre.py correctly detects the planning phase and sets the suppressed flag.

### TC-7: QA branch switching handled by cycle_pre/post
- **Result**: HUMAN-REQUIRED
- **Notes**: No pending-test items with feature branches exist to test branch switching behavior. Requires a live pending-test item with a feature branch.

### TC-8: Permissive schema — cycle_post warns on missing optional fields
- **Result**: PASS
- **Evidence**:
  - Minimal required fields only (no role-specific optionals): exit code 0, no crash.
  - Extra unexpected field `"foo": "bar"`: exit code 0, no crash, field silently ignored.

### TC-9: Missing cycle-output.json graceful handling
- **Result**: PASS
- **Evidence**: With `cycle-output.json` removed, cycle_post.py prints `WARNING: No cycle-output.json found for skill. Agent may have crashed. Skipping post-processing.` and exits 0.

### TC-10: Existing manual sub-skills not in cycle flow
- **Result**: PASS
- **Evidence**:
  - Sub-skill reference files exist: `pull-latest.md`, `git-commit.md`, `iteration-log.md` all present in `references/sub-skills/common/`.
  - `pull-latest` references in deployed CLAUDE.md files (2 per role) are in status bar documentation examples only (e.g., `pulling|pull-latest — Syncing with remote...`), not as operational instructions. The cycle-runner section handles pull/commit/push via scripts.

### TC-11: compose.py deploy-all still works end-to-end
- **Result**: FAIL
- **Evidence**:
  - `compose.py deploy-all` exits 0 successfully.
  - `tests/run_tests.py` results: 893 passed, 2 failed, 4 integration errors.
  - **Static test failures (2)**:
    1. `test_no_duplicate_opens` — Duplicate sub-skill open markers found: `['agent-lifecycle', 'cycle-runner', 'self-restart']`. In `.squidsquad/skill/CLAUDE.md`, each of these sub-skills has its `<!-- sub-skill: X -->` open marker duplicated on consecutive lines (e.g., line 222-223 both say `<!-- sub-skill: cycle-runner -->`). This is a composition bug introduced by the cycle-runner wiring.
    2. `test_dev_agent_has_working_state` — Missing `working-state.md` for boot agent. This is a pre-existing issue unrelated to FEAT-PM-2487.
  - **Integration test errors (4)**: `test_05` through `test_08` in `test_status_flow.py` — all caused by `gh issue edit` returning non-zero exit status for issue #2516. This is a transient GitHub API / issue state issue, not related to FEAT-PM-2487.
- **Root cause for FAIL**: The duplicate sub-skill markers (`agent-lifecycle`, `cycle-runner`, `self-restart`) in the deployed skill CLAUDE.md break the `test_no_duplicate_opens` composition test. This is caused by the cycle-runner wiring changes.

### TC-12: Rollout — recompose and reboot produces working agents
- **Result**: HUMAN-REQUIRED
- **Notes**: Requires running agents to reboot and monitor health for 2 cycles.

---

## Smoke Tests

| Check | Result |
|-------|--------|
| `compose.py deploy-all` exits 0 | PASS |
| No literal `[ROLE]` in any `.squidsquad/*/CLAUDE.md` | PASS |
| `cycle_pre.py pm` exits 0 and writes valid JSON | PASS |
| `cycle_post.py pm` exits 0 with minimal cycle-output.json | PASS |
| `tests/run_tests.py` — all existing tests pass | FAIL (2 static, 4 integration) |
| `grep "Cycle Runner" .squidsquad/skill/CLAUDE.md` returns matches | PASS |
| No feature flag gate text in any deployed CLAUDE.md | PASS |

---

## Test Suite Results

```
Total: 895 collected (static) + 17 (integration)
Passed: 893 static + 13 integration = 906
Failed: 2 static
Errors: 4 integration (transient GitHub API)
```

### Static Failures Detail

1. **`test_no_duplicate_opens`** — FEAT-PM-2487 REGRESSION. Duplicate `<!-- sub-skill: X -->` open markers for `agent-lifecycle`, `cycle-runner`, `self-restart` in the deployed skill CLAUDE.md. compose.py is inserting the open marker twice for these sub-skills.

2. **`test_dev_agent_has_working_state`** — PRE-EXISTING. Boot agent missing `working-state.md`. Not related to this feature.

### Integration Errors Detail

Tests 5-8 in `test_status_flow.py` fail due to `gh issue edit` returning non-zero for issue #2516. This is a transient GitHub API issue (likely the test issue was deleted or rate-limited), not related to FEAT-PM-2487.

---

## Verdict

**TC-11 FAIL blocks shipping.** The duplicate sub-skill markers in composed templates break the `test_no_duplicate_opens` test. This is a real regression introduced by the cycle-runner wiring. The composition logic in `compose.py` is inserting duplicate open markers for `agent-lifecycle`, `cycle-runner`, and `self-restart` sub-skills. This must be fixed before the feature can ship.

# FEAT-PM-2361 Test Plan — TC Coverage Gate

## Test Cases

### TC-1: Happy path — full coverage, all PASS
- **Precondition**: A TEST-PLAN.md exists with TC-1 through TC-5. A QA-RESULTS.md exists with TC-1 through TC-5, all marked PASS.
- **Steps**: Run `python references/scripts/tc_coverage.py --test-plan <plan> --qa-results <results>`.
- **Expected**: Exit code 0. Output confirms 5/5 TCs covered, 100% coverage.
- **Verification**: `echo $?` returns 0; stdout contains "5/5" and "100%".

### TC-2: Happy path — full coverage, mix of PASS and FAIL
- **Precondition**: TEST-PLAN.md with TC-1 through TC-3. QA-RESULTS.md with TC-1 PASS, TC-2 FAIL, TC-3 PASS.
- **Steps**: Run `python references/scripts/tc_coverage.py --test-plan <plan> --qa-results <results>`.
- **Expected**: Exit code 0 for coverage (all TCs accounted for). Output notes that TC-2 is FAIL. Coverage is 100% (coverage measures presence, not pass/fail).
- **Verification**: `echo $?` returns 0; output lists TC-2 as FAIL.

### TC-3: Gap detection — missing TCs in QA-RESULTS
- **Precondition**: TEST-PLAN.md with TC-1 through TC-5. QA-RESULTS.md with only TC-1, TC-3, TC-5.
- **Steps**: Run `python references/scripts/tc_coverage.py --test-plan <plan> --qa-results <results>`.
- **Expected**: Exit code 1. Output lists TC-2 and TC-4 as missing. Coverage reported as 3/5 (60%).
- **Verification**: `echo $?` returns 1; stderr or stdout contains "TC-2" and "TC-4" as missing.

### TC-4: Invalid result — "not applicable" rejected
- **Precondition**: TEST-PLAN.md with TC-1, TC-2. QA-RESULTS.md with TC-1 PASS, TC-2 marked "not applicable" (or "N/A" or "not-applicable").
- **Steps**: Run `python references/scripts/tc_coverage.py --test-plan <plan> --qa-results <results>`.
- **Expected**: Exit code 1. TC-2 flagged as having an invalid result. Only PASS, FAIL, and BLOCKED are valid.
- **Verification**: `echo $?` returns 1; output contains "invalid result" and references TC-2.

### TC-5: Invalid result — "deferred" rejected
- **Precondition**: TEST-PLAN.md with TC-1, TC-2. QA-RESULTS.md with TC-1 PASS, TC-2 marked "Deferred".
- **Steps**: Run `python references/scripts/tc_coverage.py --test-plan <plan> --qa-results <results>`.
- **Expected**: Exit code 1. TC-2 flagged as having an invalid result.
- **Verification**: `echo $?` returns 1; output contains "invalid result" or "deferred" and references TC-2.

### TC-6: Tolerant parsing — TC-01 format
- **Precondition**: TEST-PLAN.md uses `### TC-01:`, `### TC-02:`. QA-RESULTS.md uses `### TC-01:`, `### TC-02:`.
- **Steps**: Run `python references/scripts/tc_coverage.py --test-plan <plan> --qa-results <results>`.
- **Expected**: Exit code 0. Zero-padded IDs normalized correctly, matched between files.
- **Verification**: `echo $?` returns 0; 2/2 coverage.

### TC-7: Tolerant parsing — TC-1 (no zero-pad) format
- **Precondition**: TEST-PLAN.md uses `### TC-1:`, `### TC-2:`. QA-RESULTS.md uses `### TC-1:`, `### TC-2:`.
- **Steps**: Run tc_coverage.py.
- **Expected**: Exit code 0. IDs matched without zero padding.
- **Verification**: `echo $?` returns 0.

### TC-8: Tolerant parsing — "TC 01" (space instead of dash)
- **Precondition**: TEST-PLAN.md uses `### TC 01:`. QA-RESULTS.md uses `### TC 01:`.
- **Steps**: Run tc_coverage.py.
- **Expected**: Exit code 0. Space-separated format recognized and normalized.
- **Verification**: `echo $?` returns 0.

### TC-9: Tolerant parsing — cross-format matching
- **Precondition**: TEST-PLAN.md uses `### TC-01:` (zero-padded, dashed). QA-RESULTS.md uses `### TC-1:` (no zero-pad, dashed).
- **Steps**: Run tc_coverage.py.
- **Expected**: Exit code 0. Both normalize to the same canonical TC ID and match.
- **Verification**: `echo $?` returns 0; no missing TCs reported.

### TC-10: Auto-discovery by issue number
- **Precondition**: `.squidsquad/pm/planning/FEAT-PM-2361-TEST-PLAN.md` and `.squidsquad/pm/planning/FEAT-PM-2361-QA-RESULTS.md` exist. No explicit `--test-plan`/`--qa-results` args given.
- **Steps**: Run `python references/scripts/tc_coverage.py --issue 2361`.
- **Expected**: Script auto-discovers the correct TEST-PLAN and QA-RESULTS files from planning directories.
- **Verification**: Output references the discovered file paths; exit code reflects actual coverage.

### TC-11: Auto-discovery — multiple planning dirs, PM preferred
- **Precondition**: Both `.squidsquad/pm/planning/FEAT-PM-2361-TEST-PLAN.md` and `.squidsquad/skill/planning/FEAT-SKILL-2361-TEST-PLAN.md` exist.
- **Steps**: Run `python references/scripts/tc_coverage.py --issue 2361`.
- **Expected**: The PM planning dir file is selected (PM owns test plans, per CONTEXT.md).
- **Verification**: Output shows the PM path was used, not the skill path.

### TC-12: Multiple revisions — picks highest -RN
- **Precondition**: `.squidsquad/pm/planning/FEAT-PM-100-QA-RESULTS.md`, `FEAT-PM-100-QA-RESULTS-R2.md`, and `FEAT-PM-100-QA-RESULTS-R3.md` all exist.
- **Steps**: Run `python references/scripts/tc_coverage.py --issue 100`.
- **Expected**: The `-R3` revision is selected. Base and `-R2` are ignored.
- **Verification**: Output references the `-R3` file path.

### TC-13: Multiple revisions — base file used when no -RN exists
- **Precondition**: Only `.squidsquad/pm/planning/FEAT-PM-100-QA-RESULTS.md` exists (no `-RN` variants).
- **Steps**: Run `python references/scripts/tc_coverage.py --issue 100`.
- **Expected**: The base QA-RESULTS.md is used.
- **Verification**: Output references the base file path.

### TC-14: No TEST-PLAN exists — gate skipped
- **Precondition**: No `*-2361-TEST-PLAN.md` exists in any planning directory.
- **Steps**: Run `python references/scripts/tc_coverage.py --issue 2361`.
- **Expected**: Exit code 0. Output indicates no test plan found, gate skipped.
- **Verification**: `echo $?` returns 0; output contains "no test plan" or "skipped".

### TC-15: BLOCKED results — counted as covered but block shipping
- **Precondition**: TEST-PLAN.md with TC-1 through TC-3. QA-RESULTS.md with TC-1 PASS, TC-2 BLOCKED, TC-3 PASS.
- **Steps**: Run tc_coverage.py.
- **Expected**: Coverage is 3/3 (100%) — BLOCKED counts as accounted for. But exit code is non-zero (e.g., exit 2 or a distinct signal) indicating shipping is blocked due to BLOCKED results.
- **Verification**: Coverage output shows 100%; exit code or output explicitly flags BLOCKED TCs as shipping blockers.

### TC-16: --force does NOT bypass TC coverage
- **Precondition**: TEST-PLAN.md with TC-1, TC-2. QA-RESULTS.md with only TC-1. Coverage < 100%.
- **Steps**: Run `python references/scripts/tracker.py transition <number> pending-test pending-ship --role pm-lead --force`.
- **Expected**: Transition is still blocked by TC coverage gate. `--force` bypasses role authority (tracker.py line 862) but the TC coverage check is never bypassed.
- **Verification**: `echo $?` returns 1; stderr contains coverage failure message even with --force.

### TC-17: tracker.py integration — pending-test to pending-ship blocked on coverage gap
- **Precondition**: Issue #N at status `pending-test`. TEST-PLAN.md with TC-1 through TC-3. QA-RESULTS.md with only TC-1, TC-3 (TC-2 missing).
- **Steps**: Run `python references/scripts/tracker.py transition N pending-test pending-ship --role pm-lead`.
- **Expected**: Transition blocked. Exit code 1. Error message references TC coverage failure and lists TC-2 as missing.
- **Verification**: Issue labels remain at `status:pending-test`; stderr shows coverage failure.

### TC-18: tracker.py integration — pending-test to pending-ship allowed at 100% coverage
- **Precondition**: Issue #N at status `pending-test`. TEST-PLAN.md with TC-1, TC-2. QA-RESULTS.md with TC-1 PASS, TC-2 PASS.
- **Steps**: Run `python references/scripts/tracker.py transition N pending-test pending-ship --role pm-lead`.
- **Expected**: Transition succeeds. Exit code 0. Labels updated to `status:pending-ship`.
- **Verification**: `echo $?` returns 0; `gh issue view N --json labels` shows `status:pending-ship`.

### TC-19: Graceful degradation — tc_coverage.py missing
- **Precondition**: `references/scripts/tc_coverage.py` does not exist (renamed or deleted). Issue #N at `pending-test`.
- **Steps**: Run `python references/scripts/tracker.py transition N pending-test pending-ship --role pm-lead`.
- **Expected**: Transition proceeds (gate skipped). A warning is printed to stderr indicating tc_coverage.py was not found. tracker.py does not crash.
- **Verification**: `echo $?` returns 0; stderr contains warning about missing tc_coverage.py; labels updated normally.

### TC-20: Edge case — duplicate TC IDs in TEST-PLAN
- **Precondition**: TEST-PLAN.md contains `### TC-1:` twice (duplicate heading). QA-RESULTS.md has TC-1 PASS.
- **Steps**: Run tc_coverage.py.
- **Expected**: Error exit (exit code 1). Output flags duplicate TC-1 in TEST-PLAN as ambiguous.
- **Verification**: `echo $?` returns 1; output contains "duplicate" and "TC-1".

### TC-21: Edge case — extra TCs in QA-RESULTS not in TEST-PLAN
- **Precondition**: TEST-PLAN.md has TC-1, TC-2. QA-RESULTS.md has TC-1, TC-2, TC-3 (TC-3 is extra).
- **Steps**: Run tc_coverage.py.
- **Expected**: Error or warning about TC-3 being in results but not in the plan. Coverage still reported as 2/2 for plan TCs. Exit behavior per dev discretion (error recommended per RESEARCH.md).
- **Verification**: Output references TC-3 as unexpected/extra.

### TC-22: Edge case — empty TEST-PLAN (no TCs)
- **Precondition**: TEST-PLAN.md exists but contains no TC headings (only prose or empty).
- **Steps**: Run tc_coverage.py.
- **Expected**: Exit code 0. Coverage is trivially 100% (0/0). Gate skipped or passed (no TCs to verify).
- **Verification**: `echo $?` returns 0; output indicates 0 TCs found.

### TC-23: Edge case — empty QA-RESULTS (no TCs)
- **Precondition**: TEST-PLAN.md has TC-1 through TC-3. QA-RESULTS.md exists but is empty (or has no TC entries).
- **Steps**: Run tc_coverage.py.
- **Expected**: Exit code 1. All 3 TCs listed as missing. Coverage 0/3 (0%).
- **Verification**: `echo $?` returns 1; output lists TC-1, TC-2, TC-3 as missing.

### TC-24: --debug flag prints unmatched lines
- **Precondition**: QA-RESULTS.md contains lines that do not match TC patterns (prose, blank lines, non-standard formatting).
- **Steps**: Run `python references/scripts/tc_coverage.py --test-plan <plan> --qa-results <results> --debug`.
- **Expected**: Debug output includes all lines from QA-RESULTS that were not recognized as TC markers, along with line numbers or context.
- **Verification**: Debug output present on stderr or stdout; includes specific unmatched lines.

### TC-25: Prose references to TC numbers NOT counted as markers
- **Precondition**: TEST-PLAN.md has `### TC-1:` and `### TC-2:`. QA-RESULTS.md has `### TC-1: ... PASS` and a prose paragraph containing "see TC-2 for details" but no actual `### TC-2:` heading or table row for TC-2.
- **Steps**: Run tc_coverage.py.
- **Expected**: Exit code 1. TC-2 is listed as missing. The prose mention "see TC-2" is not counted as a TC result marker.
- **Verification**: `echo $?` returns 1; TC-2 listed as missing despite prose mention.

### TC-26: Table-row TC format recognized
- **Precondition**: TEST-PLAN.md uses heading format (`### TC-1:`). QA-RESULTS.md uses markdown table rows (`| TC-1 | PASS | notes |`).
- **Steps**: Run tc_coverage.py.
- **Expected**: Exit code 0. Table-row format is recognized as a valid TC marker position (per CONTEXT.md tolerant regex spec).
- **Verification**: `echo $?` returns 0; TC-1 matched across formats.

## Smoke Tests

- [ ] `python references/scripts/tc_coverage.py --help` runs without error and shows usage.
- [ ] `python references/scripts/tc_coverage.py --issue 9999` (nonexistent issue) exits cleanly with "no test plan found" message.
- [ ] `python references/scripts/tracker.py transition` still works for non-pending-ship transitions (e.g., `approved -> in-progress`) without invoking tc_coverage at all.
- [ ] `python -m pytest tests/test_tc_coverage.py` passes (unit tests for the new module).
- [ ] Existing tests (`python tests/run_tests.py`) still pass after tracker.py modifications.

## Regression Risks

- **tracker.py transition latency**: Adding a subprocess call to tc_coverage.py in the transition path may slow down all pending-test to pending-ship transitions. Verify the added time is acceptable (<2s for typical file sizes).
- **tracker.py non-ship transitions unaffected**: The gate must only fire on `pending-test -> pending-ship`. Verify that `pending-test -> in-progress`, `approved -> in-progress`, and all other transitions are completely unaffected.
- **Existing QA framework tests**: `tests/test_deterministic_qa_framework.py` must continue to pass unchanged. The TC coverage gate is additive, not a replacement for the existing framework.
- **--force behavior preserved**: `--force` currently bypasses role authority and unread-feedback guards (tracker.py lines 862, 878). After this change, `--force` must still bypass those two guards but NOT the TC coverage gate. Verify no accidental bypass leakage.
- **Auto-close on shipped still works**: The `status:shipped` auto-close logic (tracker.py line 938) must not be disrupted by the new gate insertion point.
- **Draft PR conversion on pending-ship**: The `_convert_draft_pr_to_ready` call (tracker.py line 935) fires after transition succeeds. If the TC gate blocks the transition, this call must NOT fire.

## Comprehension Questions (task modifies tracker.py — agent-consumed infrastructure)

### CQ-1: What happens when a dev agent tries to ship a task that has a TEST-PLAN but incomplete QA-RESULTS?
- **Files**: `references/scripts/tracker.py`, `references/scripts/tc_coverage.py`
- **Expected**: The transition from `pending-test` to `pending-ship` is blocked. The agent receives an error message listing the missing TCs and must ensure all TCs in the test plan have corresponding results before retrying.

### CQ-2: Can --force bypass the TC coverage gate?
- **Files**: `references/scripts/tracker.py` (transition function, around line 835-944)
- **Expected**: No. `--force` bypasses role authority and unread-feedback guards only. The TC coverage gate is never bypassed, even with `--force`. To ship without coverage in a true emergency, the human must manually close the issue via `gh issue close`.

### CQ-3: What valid result values can appear in QA-RESULTS.md?
- **Files**: `references/scripts/tc_coverage.py`
- **Expected**: Only PASS, FAIL, and BLOCKED. The values "not applicable", "N/A", "deferred", and "not-applicable" are explicitly rejected as invalid results.

### CQ-4: If no TEST-PLAN.md exists for an issue, what happens during the pending-test to pending-ship transition?
- **Files**: `references/scripts/tc_coverage.py`, `references/scripts/tracker.py`
- **Expected**: The TC coverage gate is skipped entirely. The transition proceeds normally (subject to other existing guards like role authority and unread feedback).

### CQ-5: How does tc_coverage.py handle multiple QA-RESULTS revisions (e.g., QA-RESULTS.md, QA-RESULTS-R2.md, QA-RESULTS-R3.md)?
- **Files**: `references/scripts/tc_coverage.py`
- **Expected**: It selects the highest `-RN` revision. If `-R3` exists, it is used over `-R2` and the base file. If no `-RN` variants exist, the base `QA-RESULTS.md` is used.

### CQ-6: What TC ID formats are recognized by the tolerant parser?
- **Files**: `references/scripts/tc_coverage.py`
- **Expected**: `TC-01`, `TC-1`, `TC 01`, `### TC-1:`, and table rows like `| TC-1 | PASS |`. All variants are normalized to a canonical form internally. Prose references like "see TC-1" in running text are NOT recognized as TC markers.

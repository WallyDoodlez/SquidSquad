I've now reviewed the relevant source code in `cycle_pre.py` and `cycle_post.py` to ground the two open questions against the actual codebase. Here are my findings:

---

### Finding 1

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8701.md`
- **Line**: 86 (UT-9 heading: "`### UT-9 (bonus)`")
- **Severity**: warning
- **Issue**: UT-9 is labeled "(bonus)" but it is the **only** test covering AC-5, which is a mandatory acceptance criterion ("`event-driven: yes` invocation with no task id supplied → clean exit with a clear error"). Labeling it "bonus" signals it can be skipped during implementation, which would leave AC-5 with zero test coverage.
- **Evidence**: AC-5 is listed in Section 1 alongside AC-1 through AC-11 with no indication it is optional. CONTEXT.md §5.5 lines 609–610 explicitly specifies this no-op safety behavior as a deliverable ("if invoked in events mode but no task id is supplied, exit cleanly with a clear error").
- **Suggested fix**: Promote UT-9 to a standard unit test (remove "bonus" designation). If the intent was that it's lower priority than other UTs, renumber it normally and add a priority note rather than labeling it bonus.

---

### Finding 2

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8701.md`
- **Line**: 73–75 (UT-1 verification), 1007 (cycle_pre.py call site)
- **Severity**: warning
- **Issue**: No test verifies that `_get_cycle_number()` (cycle_pre.py:329–342) is **not called** in event mode. The current code at `cycle_pre.py:1007` calls this function unconditionally in `main()`. UT-1 only verifies file outcomes (`cycle-input.json` content + `iter-6.md` absence) — it does not assert that the `_get_cycle_number` code path is gated. If the function runs, it returns a real cycle number from the `iter-N.md` files on disk, which would populate `cycle_number` in `cycle-input.json` and violate AC-3's "No cycle counter increment." The test's lenient assertion ("omitted or fixed at 0/null") would not catch this regression.
- **Evidence**: `cycle_pre.py:1007` is outside any mode-gating branch in `main()` — it runs before `cycle-input.json` is built at line 1031. UT-1 says "assert `cycle-input.json` content" but the plan defers the `cycle_number` field semantics to Open Question 2, leaving a coverage gap: the test as specified would pass even if an unwanted real number appears.
- **Suggested fix**: Add an explicit assertion that `_get_cycle_number()` is never called in event mode (mock/spy verification), or add a specific assertion that `cycle-input.json` contains no `cycle_number` field (not just "accepts any of omission/null/0"). The test should fail if the function is called and produces a live number.

---

### Finding 3

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8701.md`
- **Line**: 109–114 (NT-2)
- **Severity**: warning
- **Issue**: NT-2 verifies that `.squidsquad/<role>/current-state` file is absent after an event-mode cycle, but it does **not** verify that `_write_status_bar()` is gated (never called). A false positive could occur if the function writes the file and then some other path deletes it (or if a `.tmp` write-and-replace is rolled back). The file-absence assertion is weaker than a function-call verification.
- **Evidence**: `_write_status_bar()` is invoked at three points in `cycle_pre.py` main (line 986 "pulling", line 1011 "triaging") and at two points in `cycle_post.py` main (lines 731–733 "restarting" / "idle"). All five call sites are unconditional in the current code. If any one of them is missed during gating, NT-2's file-absence assertion might still pass (e.g., if the final write is correctly gated but earlier writes are not, the final state would be overwritten but the test wouldn't catch the intermediate writes).
- **Evidence**: AC-8 explicitly states: "Status-line file-based path (`_write_status_bar()` writes to `.squidsquad/<role>/current-state`) is a no-op in event mode." "No-op" means the function should not execute, not just that the file disappears.
- **Suggested fix**: Strengthen NT-2 to use a subprocess-call recorder or mock that asserts `_write_status_bar()` has zero invocations in event mode, OR assert that the file is never touched (check atime/mtime unchanged) rather than just absent. The current test should remain as a secondary check but should not be the sole verification of AC-8.

---

### Finding 4

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8701.md`
- **Line**: Section 5 (Negative Tests) and the open question at Section 10 ¶6
- **Severity**: warning
- **Issue**: Zero test coverage exists for cursor-advancement behavior in event mode. `_advance_event_cursor()` (cycle_post.py:587–644) is called unconditionally at `cycle_post.py:700` in the current code. Open Question 6 correctly identifies that this batch-advance-at-cycle_post-time behavior conflicts with CONTEXT.md §2's "Cursor advancement = per-event, atomic" rule. However, the test plan contains **no test** — not even a placeholder — for cursor behavior in event mode. Regardless of how OQ6 is resolved, tests will be needed: either (a) verify `_advance_event_cursor` is skipped in event mode, or (b) verify it follows a different per-task-atomic protocol. The test plan is silent on this entire area.
- **Evidence**: CONTEXT.md §2 lines 58–65: "Cursor advancement = per-event, atomic — write to `.tmp`, then `mv`. No batching. One write per processed event." `cycle_post.py:587–644` advances the cursor in a batch at cycle post time using the last event ID from `recent_events`. The test plan has no UT or IT covering what happens to the cursor in event mode. Even UT-6 (context-pressure exit 42) doesn't mention cursor state at all.
- **Suggested fix**: Add a test (UT or NT, depending on resolution of OQ6) that explicitly verifies cursor behavior in event mode. If OQ6 resolves to "skip `_advance_event_cursor` in event mode," add a negative test asserting it is never called. If it resolves to "advance per-task," add a unit test verifying the atomic per-task advance. Flag the test as blocked on OQ6 resolution in a note.

---

### Finding 5

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8701.md`
- **Line**: 108 (IT-5)
- **Severity**: warning
- **Issue**: IT-5 says "in parallel, run `cycle_pre.py skill --task 200` and `cycle_pre.py pm` (no task)." True parallel execution of these two scripts on the same git repo risks git race conditions (both call `_do_pull`, both write to `.squidsquad/` files). The verification checks per-role JSON content, which would be correct even under sequential execution. The "in parallel" wording is misleading and could cause flaky test failures from git lock contention.
- **Evidence**: Both scripts invoke `_do_pull()` (cycle_pre.py:995), read/write to the shared `.squidsquad/` directory tree, and shell out via `subprocess.run` to git commands. True parallel execution in a test harness would require explicit isolation (separate worktrees or repos) that the test preconditions do not describe. The verification assertions only check per-role files (`.squidsquad/skill/cycle-input.json` vs `.squidsquad/pm/cycle-input.json`), which would be identical under sequential execution.
- **Suggested fix**: Rephrase IT-5 to specify sequential execution within the same test (run skill first, then pm, or vice versa) while still asserting both produce the correct mode-specific outputs. If true parallelism is desired, add explicit isolation measures (separate git worktrees or temp repos) to the preconditions.

---

### Finding 6

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8701.md`
- **Line**: Section 10, Open Question 5 (referencing cycle_post.py:49)
- **Severity**: error (planning gap — not a test defect, but a blocker for test authoring)
- **Issue**: Open Question 5 correctly identifies that `REQUIRED_FIELDS = {"role", "cycle_number", "cycle_type"}` at `cycle_post.py:49` is incompatible with event mode, where there is no `cycle_number`. However, the test plan does **not** include any test for this validator relaxation — not even a placeholder. When the implementation gates the validation on mode, tests must verify: (a) event-mode `cycle-output.json` without `cycle_number` passes validation, and (b) loop-mode validation still rejects missing `cycle_number`. Currently zero tests cover `_validate_output()` at all.
- **Evidence**: `_validate_output()` (cycle_post.py:109–133) runs unconditionally in `main()` (called at line ~660 area). If event-mode `cycle-output.json` lacks `cycle_number`, the validation fails and the script exits early before any task-log, commit, or status transitions occur. This means the event-mode path cannot function at all without this fix — it's a hard blocker, not a minor relaxation.
- **Suggested fix**: Add a dedicated unit test (e.g., UT-10) for `_validate_output()` in both modes: event-mode JSON without `cycle_number` passes; loop-mode JSON without `cycle_number` still fails. This test can be designed independently of how OQ5 resolves (if `cycle_number` ends up as `null`/`0` instead of absent, adjust the fixture accordingly). Mark the exact assertion as dependent on OQ5 resolution.

---

### Finding 7

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8701.md`
- **Line**: 152–155 (PV-3)
- **Severity**: warning
- **Issue**: PV-3 states that after Phase 6 /loop deletion, event-mode tests (UT-1 through UT-6, UT-9; IT-1, IT-2, IT-3, IT-5; NT-1 through NT-4) "must continue to pass." However, these tests as specified mock the config to set `event-driven: yes`. After Phase 6, the scripts become single-mode (events-only) and may remove the config-read branch entirely. The tests may fail if they still try to mock a config flag that the scripts no longer read. PV-3 should acknowledge that tests may need a light update (removing the config mock) while the core assertions remain intact.
- **Evidence**: The post-Phase-6 scripts per CONTEXT.md §7.1 are "single-mode, events-only" — they likely won't read `event-driven: yes/no` at all. If UT-1's precondition is "role config `event-driven: yes`" and the test sets that mock, but the code no longer calls `config.get`, the mock won't match the implementation. This is a minor test-maintenance note, not a design flaw, but PV-3 makes a stronger claim ("must continue to pass") that may not hold without acknowledging the config-mock adjustment.
- **Suggested fix**: Add a note to PV-3: "Tests may require a trivial update (removing the event-driven config mock) after the /loop branch deletion; the core assertions (task-log naming, no cycle counter, etc.) must remain unchanged and continue to pass."

---

### Summary

The two open questions (OQ5: `REQUIRED_FIELDS` on cycle_post.py:49, OQ6: `_advance_event_cursor` on cycle_post.py:587) are **genuine PM-level planning gaps**, not implementation details. Both block test authoring: OQ5 blocks any validator test, and OQ6 blocks any cursor-behavior test. The test plan correctly identifies them as open but does not include placeholder tests or flagged-blocked notes for either area.

The test plan is otherwise thorough — the dual-mode coverage (UT-7, UT-8, IT-4 for loop regression; IT-5 for coexistence), negative tests (NT-1 through NT-4), migration tests (MT-1 through MT-3), and gating conditions (Section 8) are all well-structured and correctly mapped to CONTEXT.md requirements. The main gaps are: (1) UT-9's "bonus" label undermining a mandatory AC, (2) missing function-level verification for gated paths (`_get_cycle_number`, `_write_status_bar`), (3) zero cursor-advancement test coverage, and (4) zero validator test coverage.
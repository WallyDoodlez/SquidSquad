# Findings

I've reviewed TEST-PLAN-8694.md against CONTEXT.md and the review criteria. Below are the genuine issues found.

---

### Finding 1

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8694.md`
- **Line**: 325 (Traceability Matrix row for §3.5)
- **Severity**: error
- **Issue**: The traceability matrix maps CONTEXT §3.5 (Case E — Special events) to `"CQ Q3 (unknown), 4.x stop-requested (manual)"` — but section `4.x` does not exist. There is no §4.8, and no integration test anywhere in the plan that covers `stop-requested` behavior.
- **Evidence**: CONTEXT §3.5 explicitly specifies: *"stop-requested — honored ONLY at task boundary. Mid-task: read, advance, ignore. At boundary: checkpoint working-state.md (preserve cursor), exit cleanly."* This is a defined workflow case. The test plan's integration tests span §4.1–§4.7 with no stop-requested entry. The manual smoke tests in §7 also do not include a stop-requested smoke test.
- **Suggested fix**: Either add an integration test (e.g. §4.8) that pushes a `stop-requested` event mid-task and validates the agent completes the task before exiting, OR add a manual smoke test to §7 for stop-requested behavior and fix the traceability matrix reference to point to the correct section.

---

### Finding 2

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8694.md`
- **Line**: 318 (Traceability Matrix row for §3.2)
- **Severity**: warning
- **Issue**: CONTEXT §3.2 (Case B — Idle, event arrives) lacks a dedicated integration test. The traceability matrix maps it to `4.1, CQ Q4`, but integration test 4.1 is the "happy-path end-to-end" test that covers boot→work→completion, not the specific "agent is idle in cool-down loop, a relevant event arrives, agent wakes and runs work_queue()" flow.
- **Evidence**: CONTEXT §3.2 specifies: *"1. Read event at cursor+1. 2. Forge-read the referenced item (if any) via tracker.py. 3. Run work_queue(role) against the forge — pick up if available, else stay idle."* The only test exercising idle→event→pickup is a manual smoke test (§7.3 "Cool-down cancellable by event"), not an automated integration test. Given that Cases A, C, and D all have automated integration or negative-test coverage, the gap for Case B is uneven.
- **Suggested fix**: Either add a brief integration test (e.g. §4.1 step variant: let agent enter idle cool-down, then push a relevant event, assert agent wakes before `Next scan after` and calls `work_queue()`), or acknowledge the gap explicitly and update the traceability matrix to reference the manual smoke test §7.3 honestly rather than claiming §4.1 covers it.

---

### Finding 3

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8694.md`
- **Line**: 109–111 (§3.7) and 232–233 (§6.6)
- **Severity**: warning
- **Issue**: The same grep-guard test `test_no_mode_conditional_strings_in_event_fragments` is specified twice — once under §3.7 ("Compose round-trip") and once under §6.6 as a negative test. Both are described identically as "Recursive grep guard (AC-5)."
- **Evidence**: §3.7 bullet 2: `test_no_mode_conditional_strings_in_event_fragments` — "Recursive grep guard (AC-5)." §6.6: `test_no_mode_conditional_in_event_fragments` — "Grep guard. The string event-driven: must not appear as a branching instruction inside any event-mode fragment body." Two sections claim ownership of the same test with slightly different names. This creates ambiguity about which test file owns it and risks double-implementation or conflicting implementations.
- **Suggested fix**: Keep it in only one location (preferably §6.6 as a negative test, since that's its nature). Remove the duplicate from §3.7 and cross-reference §6.6 instead, or consolidate into a single canonical test.

---

### Finding 4

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8694.md`
- **Line**: 64–67 (§4 contents list) and CONTEXT §2 (§"Event stream gap behavior — three scenarios")
- **Severity**: warning
- **Issue**: CONTEXT §2 defines three gap scenarios: (1) in-stream gap, (2) long cursor lag (24h+), and (3) eviction gap. Only the eviction gap is tested (§4.4). The other two scenarios — "in-stream gap (small missing range within the retained window): log warning, advance cursor past the gap, continue" and "long cursor lag (24h+) — skim-then-advance for audit fidelity, not jump-to-latest" — have no corresponding tests in the plan.
- **Evidence**: CONTEXT §3.1 step 3 explicitly requires: *"Handle gap scenarios per §2 (in-stream gap / long lag / eviction gap)."* Only eviction gap is addressed. The in-stream gap scenario is testable (seeded cursor at N, events exist at N+2 and N+3 but not N+1). The long-lag scenario (cursor lagging far behind) tests the "skim-then-advance, never jump-to-latest" rule which is distinct from the eviction case.
- **Suggested fix**: Add two gap-scenario tests (or at minimum, one combined test): (a) in-stream gap: seed cursor with a gap, assert warning logged and cursor advances past the gap; (b) long-lag: seed cursor at 0 with 50+ events accumulated, assert the agent skims events sequentially (does not jump to latest) and advances cursor incrementally, not in one jump.

---

### Finding 5

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8694.md`
- **Line**: 74–81 (M-2.1 items a–e)
- **Severity**: warning
- **Issue**: M-2.1 item (b) states the agent must *"call tracker.py work-queue <role> exactly once before any harness call"* — but this assertion is only correct when the agent boots into the **idle** state. If working-state shows an in-progress task (AC-2 §3.1 step 2 first branch), the agent must call `tracker.py get-state` (forge verification) before `work_queue()`, or may not call `work_queue()` at all if it resumes the task. The M-2.1 refinement is ambiguous about which boot scenario it applies to.
- **Evidence**: Integration test 4.5 step 1 correctly pre-conditions: *"Pre-seed working-state.md to idle."* But M-2.1 itself doesn't state this pre-condition. When read in isolation (as acceptance criteria refinements are meant to be), M-2.1(b) is over-specified and would incorrectly fail if applied to a non-idle boot scenario.
- **Suggested fix**: Amend M-2.1 to read: *"With working-state.md pre-seeded to idle (no in-progress task, no scan running), a fresh agent session must (a) load working-state.md, (b) call tracker.py work-queue <role> exactly once before any harness call..."* — making the scenario explicit.

---

### Finding 6

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8694.md`
- **Line**: 154–158 (§5.2, CQ spec `files` list)
- **Severity**: error
- **Issue**: The comprehension test spec's `files` list includes `references/sub-skills/roles/dm/events/pr-merge-wait.md` — a role-specific fragment for DM — but the comprehension questions are about the **event-mode L1 base agent definition**, which is a role-agnostic contract. Questions Q5 and Q6 reference DM behavior, but the spec does not include any per-role fragments for PM, skill, or QA, yet the test is supposed to validate the full event-mode L1 base agent definition (which per CONTEXT §5.1 deliverables includes *"Updates to per-role events fragments (skill / pm / qa / dm) for role-specific behavior on top of the common contract"*).
- **Evidence**: AC-4 (M-4.1) requires: *"Spec files list MUST contain only fragments under references/sub-skills/common-events/ and per-role references/sub-skills/roles/<role>/events/ (no project-level L4, no SOUL, no CONTEXT.md)."* But it does not require completeness — it only restricts what's included. Meanwhile, Open Question #5 acknowledges: *"Whether PM/QA/skill need their own role-specific events fragments at all (or can rely on common-events/) is not locked."* The CQ spec includes DM's fragment but silently omits the other three roles. If those fragments don't exist yet, the CQ spec's question set should not depend on them. If they do exist, they should be included. The current state is inconsistent: DM gets a role-specific fragment in the spec, but PM/QA/skill don't.
- **Suggested fix**: Either (a) remove `pr-merge-wait.md` from the CQ spec until all per-role fragments are locked and included symmetrically, or (b) add a note that the CQ spec will be extended with per-role fragments when Open Question #5 is resolved. Q5 and Q6 should still be answerable from `l1-base.md` and `comment-handling.md` alone, so removing the DM-specific fragment shouldn't break the comprehension test.

---

### Finding 7

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8694.md`
- **Line**: 297–301 (Post-ship validation §9.2, Probe A)
- **Severity**: error
- **Issue**: Probe A says: *"Harness kill mid-operation: stop the harness while a role is mid-task. Confirm: Agent does NOT pivot to forge-direct (negative test 6.3 in production). event_poll.py retries with capped backoff (verifiable from stderr log, retries ≤ 5 min apart). When harness restarts, agent reconnects via event_poll.py and the next event flows through."* — This contradicts the architecture decision in CONTEXT §5.1 and §11 glossary that mid-operation harness failure is a **manual-recovery scenario**. The probe claims the agent *"reconnects via event_poll.py and the next event flows through"* automatically, but the CONTEXT states: *"the agent simply retries event_poll.py at the same 5-minute cap until the harness returns, relying on the L1 failsafe boot path if the operator restarts the agent."* The probe is testing for automatic recovery that the architecture doesn't guarantee — the agent retries but may need operator restart.
- **Evidence**: CONTEXT §11 glossary "Degraded mode": *"Mid-operation harness failure (after bootup-complete) does NOT trigger degraded mode — the agent simply retries event_poll.py at the same 5-minute cap until the harness returns, relying on the L1 failsafe boot path if the operator restarts the agent."* The phrase "if the operator restarts the agent" implies automatic reconnection isn't guaranteed. Probe A asserts it as a pass condition, which may not hold.
- **Suggested fix**: Rephrase Probe A to: *"Confirm: (a) Agent does NOT pivot to forge-direct. (b) event_poll.py retries with capped backoff. (c) Agent completes or checkpoints its current task and logs its state to the forge. (d) After harness restart AND agent restart (if needed), the agent boots and recovers state from the forge."* This aligns with the documented degraded-mode boundary.

---

### Summary of Findings

| # | Severity | Issue |
|---|----------|-------|
| 1 | error | Dead reference "4.x" in traceability matrix; no stop-requested test exists |
| 2 | warning | Case B (idle/event) has no automated integration test |
| 3 | warning | Duplicate test specification for mode-conditional grep guard |
| 4 | warning | In-stream gap and long-cursor-lag scenarios have no tests |
| 5 | warning | M-2.1(b) is ambiguous about boot scenario pre-condition |
| 6 | error | CQ spec includes DM role fragment but not PM/skill/QA; inconsistent |
| 7 | error | Probe A asserts automatic reconnect that architecture does not guarantee |
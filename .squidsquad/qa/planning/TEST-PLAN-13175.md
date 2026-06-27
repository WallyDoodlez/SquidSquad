# TEST-PLAN-13175 — Case E deploy-signal boot-drain ambiguity

**Source**: GitHub issue #13175 + skill RCA resolution (PR #13177).
**Derived without reading the diff.**

LLM-consumed instruction (event-mode-contract.md Case E). The RCA overturned the issue's
premise: harness is already correct; defect is **contract ambiguity**; fix = a boot-drain
deploy-signal must be **HONORED** (inverts the issue's direction-(b)).

## ACs
- **AC-1** — Contract resolves the boot-drain deploy-signal honor-vs-skip ambiguity correctly
  (honor; do not dismiss as residual telemetry).
- **AC-2** — Two traps documented: (a) don't self-assess drift from the local clone and skip
  (harness checksum authoritative); (b) don't manually `ack-cursor` past it (leaves stale CLAUDE.md).
- **AC-3** — Brittle fixed-char-window test re-anchored to content.

## Test Cases

### TC-1 (AC-1, AC-2): Comprehension — fresh agent derives correct action
- **Method**: fresh sonnet agent given ONLY the modified event-mode-contract.md, no other context.
- **Expected**: CQ1 honor (not residual; checksum authoritative); CQ2 don't ack-cursor past (stale-CLAUDE.md risk; loop-free); CQ3 finish-first then honor.
- **Artifact**: `tests/comprehension/13175_spec.json`.

### TC-2 (premise fact-check): Contract claims hold against harness.py
- **Expected**: cursor advanced up-front in deploy seq (harness.py:4646); ack-stop deploy-halted
  sets intent=DEPLOYING synchronously on boot-drift path (3252-3263); boot deploy-signal on checksum drift.
- **Verification command**: `grep`/`sed` over `references/scripts/harness.py`.

### TC-3 (AC-3): Test anchor fix passes + no regression
- **Expected**: `test_event_contract_states_loop_mode_does_not_consume` passes; full `tests/run_tests.py` green.
- **Verification command**: pytest on the branch + `tests/run_tests.py`.

## Coverage matrix
- AC-1 → TC-1 (CQ1), TC-2
- AC-2 → TC-1 (CQ2, CQ3)
- AC-3 → TC-3

## Comprehension Questions
See `tests/comprehension/13175_spec.json` (3 CQs). This is the hard gate (#9184). Result: 3/3 PASS.

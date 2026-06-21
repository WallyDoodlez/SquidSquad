# QA-RESULTS-13175 — Case E deploy-signal boot-drain ambiguity

**Verifier**: qa
**Date**: 2026-06-21 19:33
**Verdict**: PASS — zero gaps. Status → Pending Ship.
**Change under test**: PR #13177, branch `squidsquad/task/13175` (event-mode-contract.md + test anchor fix).

## AC walk (issue body + skill's RCA resolution)

The RCA overturned the issue's own premise (facts-verified vs harness.py): the harness is already
correct; the defect is **Case E contract ambiguity**, and the fix INVERTS the issue's proposed
direction-(b) — a boot-drain deploy-signal must be **HONORED**, not skipped as residual telemetry.

| AC | Result |
|----|--------|
| AC-1 Contract resolves the honor-vs-skip ambiguity correctly (boot-drain deploy-signal = honor) | PASS |
| AC-2 Two traps documented (no local-drift self-assess; no manual ack-cursor-past) | PASS |
| AC-3 Brittle fixed-char-window test anchored to content | PASS |

## Independent fact-check of the contract's premises (against harness.py — not the diff)

The contract guidance is only correct if its claims about harness behavior hold. Verified:
- **Cursor advanced up-front in deploy sequence** — `_run_deploy_sequence` advances the cursor past
  the deploy-signal before respawn (harness.py:4646-4658, retry + loud-log). ⇒ "honoring is loop-free" ✓
- **ack-stop deploy-halted establishes intent=DEPLOYING synchronously on the boot-drift path** —
  harness.py:3252-3263 ("the emit side does NOT pre-set intent... THIS is where DEPLOYING is established
  — synchronously"). Matches the contract's parenthetical exactly. ✓
- **Boot deploy-signal emitted on checksum drift / absence** — checksum compare + drift-triggers-recompose
  present (harness.py ~549-607). ⇒ local-drift self-check is NOT authoritative ✓

## Comprehension Test (LLM-consumed instruction — #9184 hard gate)

Fresh sonnet agent (id `a5ba24e5a5693bd5e`) given ONLY the branch's modified event-mode-contract.md,
no other context. Spec: `tests/comprehension/13175_spec.json`. **3/3 correct, zero must_not violations**:
- CQ1 → honor (don't dismiss as residual; harness checksum authoritative).
- CQ2 → don't ack-cursor past (the one path that leaves a stale CLAUDE.md; honoring is loop-free).
- CQ3 → finish-first then honor (precondition: on main, clean tree).

## Test anchor fix (AC-3)

`test_event_contract_states_loop_mode_does_not_consume` now scopes its search to the deploy-signal item
(`txt[idx:txt.find("from another agent", idx)]`) instead of a fixed 4000-char window that broke when the
boot-drain paragraph grew the item. PASS on the branch (deploy module: 4 selected pass; full gate below).

### Full gate
`tests/run_tests.py` on the 13175 branch: `4892 passed, 17 skipped, 12 subtests passed`;
static-gate verdict `PASS — 4921 gated test(s) passed (0 failures, 0 errors)`. (The 4-test
delta vs #13176's 4925 is exactly #13176's 4 new tests — consistent.)

## Coverage matrix
- AC-1 → Comprehension CQ1 + harness fact-check ✓
- AC-2 → Comprehension CQ2 + CQ3 ✓
- AC-3 → test anchor PASS + full gate ✓

## Notes
LLM-consumed instruction: comprehension spec is the hard gate (PASS). Contract premises independently
verified against harness.py (facts over the diff). No HUMAN-REQUIRED TCs.

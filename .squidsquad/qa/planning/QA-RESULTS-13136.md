# QA-RESULTS-13136

**Issue**: #13136 — stop-requested handler lacks explicit ack-stop emission + ack-cursor guidance (vs deploy-signal)
**PR**: #13149 (branch squidsquad/task/13136 @ 25ab61d54, base main, +5/-3, 2 files)
**Verdict**: ✅ **PASS — zero gaps**
**Verified by**: verifier (qa), 2026-06-21 14:58
**Method**: Independent TEST-PLAN from issue's two gaps; ground-truth verification against origin/main harness.py + AGENT-RUNTIME; fresh-agent comprehension test; full regression suite on the PR branch (clean worktree).

## AC Walk

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | AC1 ack-stop explicit | PASS | Case E now has "**Do NOT emit `ack-stop` on this path.**" with rationale |
| TC2 | AC2 ack-cursor explicit | PASS | Case E now has "**Nothing to `ack-cursor`.**" — intent flip, not a deque event |
| TC3 | AC3.1 §5.2 reserved | PASS | `git show origin/main:docs/AGENT-RUNTIME.md` L334: stop-requested in "Speculative RECOGNIZED... never emitted under v1, dead weight" |
| TC4 | AC3.2 harness no emit | PASS | harness.py has no stop-requested emission; sole hit L3194 is a defensive ack handler |
| TC5 | AC3.3 §10 Q11 enum | PASS | AGENT-RUNTIME L1326: ack-stop.result = checkpointed/aborted/drained, "Closed (2026-05-30)" — exact match incl. date |
| TC6 | AC3.4 no agent ack_stop | PASS | Zero call sites of `ack_stop(` across agent scripts; only a doc-string ref in event_catalog.py:99 |
| TC7 | AC3.5 60s force-kill | PASS | harness.py L110 `FORCE_KILL_TIMEOUT_SECONDS=60`, armed on stopping/restarting intent (L256-257, 276) |
| TC8 | AC4 comprehension | PASS | Fresh sonnet agent a4661196: 3/3 correct, zero must_not. See tests/comprehension/13136_spec.json |
| TC9 | AC5.1 consistency | PASS | Stopping path (no ack-stop) vs deploy path (ack-stop=deploy-halted) clearly distinct; both files consistent; no contradiction with Soul stop-rules (sanctioned lifecycle end) |
| TC10 | AC5.2 regression | PASS | `python tests/run_tests.py` on PR worktree: 53 tests OK (skipped=2), incl. TestStopRequestedAtomicity (corroborates bus-level stop-requested is inert) |

## Findings

Both gaps in the issue are closed and the open question is resolved correctly against ground truth:
- **Gap 1 (ack-stop)**: resolved — no agent-side code emits a stop ack-stop (zero call sites confirmed); 60s force-kill is the mechanism; handler now says "emit nothing unless/until such an emission is implemented."
- **Gap 2 (ack-cursor)**: resolved — intent-driven, not a deque event → no event id to ack; cursor harness-owned + preserved.

All 5 factual claims independently verified true against origin/main. Comprehension hard gate PASS. No regression. The reframe (intent-driven, not a bus event) is consistent with §5.2 and the sibling #13134 fix.

## Disposition

Verdict PASS → transition pending-test → pending-ship. No closing keyword in PR #13149; merge + ship + counter deferred to DM per install pattern (verifier owns no release state). Comprehension spec tests/comprehension/13136_spec.json preserved permanently.

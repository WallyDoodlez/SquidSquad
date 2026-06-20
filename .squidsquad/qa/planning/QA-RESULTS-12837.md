# QA-RESULTS-12837 — Harness anchorless eviction marker kills event listener

**Verdict: PASS — zero gaps** → pending-ship (DM).
**Date:** 2026-06-19 22:57 · **Verifier:** qa · PR #12959 @ b400de7e4 · branch `squidsquad/task/12837`.

Bug (type:issue, auto-approved), filed by qa. Code-only harness fix → no CQ.
Verified in isolated worktree `D:\Dev\Dev\sq-12837-verify`. Append-only.

## Self-relevant
This is the exact bug that killed THIS verifier session's Monitor (event_poll exit 2,
"eviction with empty batch and no oldest_id anchor"). Surfaced for QA via the idle-driver
cron safety-net forge-read after the Monitor death — the missed-nudge backstop working
as designed. (Fix takes effect on the next harness restart; it does not retroactively
revive this session's dead listener.)

## Fix summary
`EventStream.get_since_with_eviction` (harness.py:1445-1471): when the cursor predates
the retained window AND the deque is EMPTY (no anchor possible), return `([], None)` —
a benign empty result with NO eviction marker — instead of building the self-
contradictory `evicted:true` + `events:[]` + `oldest_id:None` triple. When the deque is
non-empty, `oldest_id = items[0].get("id")` is always a real id. Exactly the remediation
direction in the bug report. Source-level fix; both endpoints already gate on the marker.

## AC walk (derived from bug report root-cause + remediation; all PASS)
- **AC1 (root-cause fix)** PASS — empty deque + stale cursor → `([], None)`, fatal triple
  cannot be emitted. **Independent live repro** (branch EventStream): `events=[] marker=None`.
  Test: test_empty_deque_with_evicted_cursor_suppresses_marker.
- **AC2 (marker integrity)** PASS — marker, when emitted, always carries a real `oldest_id`.
  Live: non-empty deque + stale cursor → `marker={'oldest_id':'e0',...}`.
  Test: test_eviction_marker_oldest_id_is_never_none.
- **AC3 (endpoint propagation)** PASS — `/events` (harness.py:3052) and `/events/for/{role}`
  (harness.py:3131) both set `response["evicted"]=True` ONLY under `if eviction is not None:`
  → a None marker yields a plain `{events:[], total}` (no evicted/oldest_id keys). The
  source returning None marker fully suppresses the fatal triple end-to-end.
- **AC4 (recoverable variant intact)** PASS — non-empty deque + stale cursor still emits a
  marker with real `oldest_id` (the boot-time recoverable eviction-gap path). Live-proven (B).
  Test: test_cursor_evicted_returns_marker_with_oldest_id retained.
- **AC5 (guard preserved)** PASS — `event_poll.py` is NOT in the PR diff; its fatal guard
  for a genuinely-unrecoverable case remains as defense-in-depth (now unreachable from the
  harness, by design).
- **AC6 (regression test)** PASS — test_eviction_signal.py renamed/added the two cases that
  lock the contract; would have caught the original defect (the old test asserted
  `oldest_id is None`, which was the defect being shipped).
- **No CQ** — harness code + test only, no LLM-consumed instruction change.

## No-regression
- test_eviction_signal.py → 16 passed.
- Full static gate: `python tests/run_tests.py static` → **PASS — 4653 gated tests, 0 failures, 0 errors** (exit 0). Only the 2 allowlisted #10360 known-failures, unchanged.

## Disposition
pending-test → **pending-ship** (DM). No closing keyword on PR #12959, no review:human-required
→ merge deferred to DM (delivery ownership). Counter NOT bumped. TEST-PLAN-12837 + QA-RESULTS-12837 on main.

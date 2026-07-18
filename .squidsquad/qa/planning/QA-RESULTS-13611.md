# QA-RESULTS-13611

## Summary
VERIFIED — PASS. All 8 ACs confirmed. This is my own filed improvement-scan finding; verified it exactly as I would any other item — independent re-derivation of the ACs from the issue text, live re-grep for sibling occurrences, and the canonical static gate.

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS | `git diff origin/main -- references/scripts/harness.py`: the idle-wait loop now calls `state._read_agent_clone_file(role, agent, "current-state")` instead of reading `SQUIDSQUAD_DIR / role / "current-state"` |
| AC2 | PASS | Diff: `if content is None or not content.startswith("idle"): all_idle = False; break` — a `None` result now flips `all_idle` instead of being silently swallowed |
| AC3 | PASS | `test_missing_clone_file_is_not_treated_as_idle` — confirms the loop keeps polling (sleep_calls > 1) rather than breaking on the first check when the clone file is absent |
| AC4 | PASS | `test_harness_root_stale_idle_file_ignored` — a stale "idle" file at the harness-root path with a genuinely non-idle clone state still keeps the loop polling |
| AC5 | PASS | Diff reuses `_read_agent_clone_file` (the #13558 shared helper) rather than reimplementing clone resolution |
| AC6 | PASS | `test_13611_teardown_idle_wait_clone.py` — 3/3 pass, covering exactly the three scenarios above (fast-idle-break, missing-file, stale-harness-root) |
| AC7 | PASS | Independent `grep -n "SQUIDSQUAD_DIR / role" references/scripts/harness.py` — zero hits post-fix |
| AC8 | PASS | `comprehension_staleness.py check` exits 0 clean; canonical static gate: **5631/5631 gated tests PASS, 0 failures/0 errors** |

## Zero-gap check
No gaps.

## Verdict
PASS → pending-ship.

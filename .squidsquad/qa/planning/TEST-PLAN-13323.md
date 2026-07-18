# TEST-PLAN #13323 — wizard.py stale ./start.sh docstring refs

**Derived from the issue body "Suggested fix" — not the diff.** (My own prior scan finding.)

Bug: after #13318 moved the launcher to `.squidsquad/start.sh`, two wizard.py
docstrings still described the old repo-root `./start.sh`. Cosmetic/maintainability
only — the functional `cold_start_cmd` was already correct.

## Acceptance Criteria (independent reading — scope = wizard.py per issue title/body)

| AC | Contract |
|----|----------|
| AC1 | the two wizard.py docstring refs now say `.squidsquad/start.sh` |
| AC2 | no bare `./start.sh` remains in wizard.py |
| AC3 | functional `cold_start_cmd` unchanged (`.squidsquad/start.sh`) |

## Verification (branch squidsquad/task/13323)

| TC | AC | Check | Result |
|----|----|-------|--------|
| TC1 | AC2 | `grep './start.sh' wizard.py` | **PASS** (CLEAN — none) |
| TC2 | AC1 | both docstrings (L1180, L3247) say `.squidsquad/start.sh` | **PASS** |
| TC3 | AC3 | `cold_start_cmd: ".squidsquad/start.sh"` (L1193) unchanged | **PASS** |

Regression guard: `TEST-13323-tests.py` (3 source-text asserts) — all PASS.
No behavioral surface → worker's "no unit test warranted" justification accepted
(verification.md §2b). No comprehension spec (Python docstrings, not agent instructions).

## Out-of-scope siblings (from my prior scope-expansion comment) — NOT reblocked

- `tests/test_12825_harness_restart.py` L144 docstring still says `restart-harness.sh`.
- `tests/comprehension/12420_spec.json` uses `./start.sh` as a conceptual cold-start
  foil (discriminator is per-alias-vs-cold-start, not the path string → borderline-fine).

Both are outside #13323's stated wizard.py scope. Filed as a separate low-sev follow-up
rather than reblocking #13323. A verifier comment cannot expand an issue's ACs.

# TEST-PLAN-13156

**Issue**: #13156 — harness POST /events crashes (500) on unescaped control char; should fail closed (400)
**Type**: type:issue (auto-approved), severity:medium, role:skill
**PR**: #13157 (branch squidsquad/task/13156 @ c742bddcf, base main, harness.py +14/-1 + test +78)
**Authored by**: verifier (qa), derived from the issue's observed-behavior + impact + reproduction. Independent of PR.

## Derived Acceptance Criteria

- **AC1 (fail closed)**: `POST /events` with a body containing a raw (unescaped) control char returns **400** (not 500), logs + drops the event, and is NOT recaptured as a 500 by the global handler.
- **AC2 (regression test)**: A regression test exists that reproduces the original failure (control-char body) and asserts 400 — i.e., it would have FAILED (500) before the fix.
- **AC3 (no over-rejection)**: A well-formed body with a properly-escaped multi-line string is still accepted (200).
- **AC4 (no regression)**: Full static gate green.

## Test Cases

| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC1 | AC1 | Run test_13156 raw-newline case on fixed branch | 400, _persist_harness_error NOT called |
| TC2 | AC2 | Revert ONLY harness.py to origin/main, re-run TC1 | Test FAILS (500≠400) — proves it catches the original bug |
| TC3 | AC3 | Run well-formed-body control test | 200 (accepted) |
| TC4 | AC1 | Inspect harness.py diff | try/except (json.JSONDecodeError, ValueError) → HTTPException(400) + _log |
| TC5 | AC4 | `python tests/run_tests.py static` on fixed branch | PASS, new tests included |

## Notes
- Out-of-scope-but-noted: the emit-path SOURCE posting unescaped control chars (issue names deploy-error multi-line detail as the plausible trigger) is "and/or"/optional per the issue; fail-closed is the headline requirement. The retry loop now degrades to clean 400s. Flag to PM, do not reblock.

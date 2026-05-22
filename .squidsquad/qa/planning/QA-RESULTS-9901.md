# QA Results — #9901 (cycle.py status_bar hardening + consolidate 3 drifted copies)

**Verifier**: qa-lead
**Timestamp**: 2026-05-22 09:01 cycle 726
**PR**: #9911 (branch `squidsquad/task/9901`)
**Verdict**: PASS — zero gaps. Status → Pending Ship.

## Acceptance Criteria

| # | AC | Evidence | Result |
|---|----|----------|--------|
| 1 | Single canonical writer in `cycle.status_bar`; `cycle_pre`/`cycle_post` delegate | `cycle_pre.py:L93-105` and `cycle_post.py:L117-129` both `from cycle import status_bar` (verified via `inspect.getsource`) | PASS |
| 2 | `mkdir(parents=True, exist_ok=True)` for first-spawn | `cycle.py:L92` — behavioral spot-check: status_bar('phantom-role', 'idle', 'spot-check') on a fresh tmpdir created the role-dir and wrote the file | PASS |
| 3 | All `OSError` paths swallowed and logged to stderr (role + phase + exc) | `cycle.py:L96-104` — `print(f"WARNING: status_bar write failed for {role}/{phase}: {e}", file=sys.stderr)` | PASS |
| 4 | Orphan `.tmp` cleanup after replace failure (guarded `unlink(missing_ok=True)` inside inner try) | `cycle.py:L105-108` — `test_replace_failure_does_not_raise_9901` asserts the orphan is removed | PASS |
| 5 | Unit tests cover write/mkdir/replace failure paths | 6 new tests in `tests/test_cycle.py::TestStatusBar` (missing-dir, disk-failure, mkdir-failure, replace-failure, consolidation pre, consolidation post) | PASS |

## Test runs

- `pytest tests/test_cycle.py tests/test_cycle_post.py -v` → 124 passed, 0 failed (29.98s)
- `pytest tests/test_cycle.py -k 9901 -v` → 6 passed (the new tests)
- `python tests/run_tests.py` (canonical integration runner) → 50 passed, 1 skipped, exit 0 (71.5s)

## Behavioral spot-check

Independent of unit tests, called `cycle.status_bar('phantom-role', 'idle', 'spot-check')` against a fresh `tempfile.TemporaryDirectory()` (no role dir, no parent). Function returned `'idle|spot-check'` and wrote the expected content. The pre-fix failure mode (`FileNotFoundError` on first spawn) is gone.

## Non-blocking flag for DM

PR also includes a 2-line `.squidsquad/config.md` drift — PR branch is at version 0.41.0 / shipped-since-bump 10; main has advanced to 0.42.0 / counter 0 since the PR was opened. GitHub reports `mergeable: MERGEABLE, mergeStateStatus: CLEAN`, so this is a stale-rebase artifact, not a QA defect. Flagging so DM is aware the merge may quietly revert the version bump if not handled — DM's call at ship time.

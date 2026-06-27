# QA-RESULTS-13262 — git_ops _run/_run_list subprocess timeout

**Verdict: PASS — zero gaps.** PR #13272 merged (squash). (skill-filed during #13211 DS-review; the every-agent git-subprocess hardening.)

## AC walk (independent — derived from issue body)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | `_run` passes `timeout=` to subprocess.run (default 300) | PASS |
| AC2 | `_run_list` also gets `timeout=` | PASS |
| AC3 | `TimeoutExpired` → check=False returns CompletedProcess(rc=124); check=True raises CalledProcessError(124) | PASS (real subprocess) |
| AC4 | `SQUIDSQUAD_GIT_TIMEOUT` env override (positive int) respected; invalid/non-positive → default; no config-schema change | PASS |
| AC5 | per-call `timeout=` override honored | PASS |
| AC6 | no-regression: normal git ops unaffected | PASS |

## Evidence
- Code (git_ops.py): `DEFAULT_GIT_TIMEOUT=300`, `_git_timeout()` (env override), `_timeout_failure()` (translate TimeoutExpired → rc=124 / raise). `_run` + `_run_list` both wrap `subprocess.run(..., timeout=...)` in try/except → `_timeout_failure`. **Bonus coverage:** `commit()` now routes through `_run_list` (a hung pre-commit hook is covered), and `push()` got its own 60s timeout.
- skill tests (test_git_ops.py): 13 incl. default/per-call/env-override/invalid-env(not-int, 0)/rc-124/raise/commit-routing/push-timeout — all mocked subprocess. PASS.
- **QA independent REAL-subprocess test** (`tests/test_feat_13262_git_timeout_realtime.py`): drives an actual overrunning subprocess (the running Python interpreter as a portable sleeper) past a 1s timeout — proves the `timeout=` is wired to the LIVE `subprocess.run` and the rc=124 / raise translation fires end-to-end (skill's tests only mock the raise). ALL PASS.
- No-regression: full `tests/test_git_ops.py` = 177 passed, 0 failures.

## Notes
- rc=124 is the conventional timeout exit code; check=False callers fall into their existing `returncode != 0` recovery (preserves the established contract). The #13211 `_ENSURE_MAIN_LOCK` no longer risks an indefinite hang starving the recompose surface.
- Branch predated #13267/#12801/#13169 → its diff showed those as "reverted" (staleness); merged main into the branch first so the squash carries ONLY the timeout delta (verified #13267's `--no-rebase` preserved post-merge).

Status: pending-test → pending-ship.

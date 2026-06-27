# TEST-PLAN-13262 — git_ops _run/_run_list subprocess timeout

**Derived independently** from the issue body (skill-filed during #13211 review).

## Expected behavior
`git_ops._run` / `_run_list` must enforce a subprocess timeout so a hung `git` (network stall, stuck index.lock, credential-helper wedge) fails fast into the callers' existing failure paths instead of blocking the thread (and, since #13211, the recompose surface behind `_ENSURE_MAIN_LOCK`).

## ACs
- AC1 `_run` timeout= (default 300)
- AC2 `_run_list` timeout=
- AC3 TimeoutExpired → rc=124 (check=False) / raise CalledProcessError (check=True)
- AC4 SQUIDSQUAD_GIT_TIMEOUT env override; invalid/non-positive → default; no config-schema change
- AC5 per-call override
- AC6 no-regression

## Method
- **Real subprocess** (`tests/test_feat_13262_git_timeout_realtime.py`): overrun a 1s timeout with a python sleeper, assert rc=124 / raise — proves the timeout= is wired live.
- skill's mocked TestRunTimeout (default/override/env/raise) + full `tests/test_git_ops.py`.

## Merge note
Branch predates #13267/#12801/#13169 → bring main in first so the squash carries only the timeout delta (don't revert #13267's `--no-rebase`).

# QA Results — #9930 (state_bus.commit_and_push: credential override + timeout + rebase pull)

**Verifier**: qa-lead
**Timestamp**: 2026-05-22 12:01 cycle 732
**PR**: #9931 (branch `squidsquad/task/9930`)
**Verdict**: PASS — zero gaps. Status → Pending Ship.

## Acceptance Criteria (3 layers + 4 DS pass-2 findings)

| # | AC | Evidence | Result |
|---|----|----------|--------|
| L1 | Credential override prefixed to push, retry-pull, and remote-prune | `_GH_CREDENTIAL_OVERRIDE = ["-c", "credential.helper=!gh auth git-credential"]` at state_bus.py:54-55. Diff confirms it's prepended to all three git commands in `commit_and_push`. Test `test_push_uses_gh_credential_override` and `test_retry_pull_uses_credential_override`. Behavioral: `state_bus._GH_CREDENTIAL_OVERRIDE` returns the expected list. | PASS |
| L2 | Per-call timeout via `_run(timeout=…)`, rc=124 + stderr diagnostic on `TimeoutExpired`; default `None` for backcompat | `_run` signature changed to `(cmd, check=True, cwd=None, timeout=None)`. `try/except TimeoutExpired` returns `CompletedProcess(returncode=124, stdout=(e.stdout or ""), stderr=(e.stderr or "")+msg)`. `DEFAULT_GIT_TIMEOUT = 120` passed by push, pull, and prune calls. Tests: `test_default_git_timeout_is_bounded`, `test_run_returns_124_on_timeout`, `test_run_passes_timeout_to_subprocess`, `test_run_default_timeout_is_none_for_backcompat`, `test_push_bounded_by_default_timeout`. Behavioral: `_run([python, '-c', 'sleep(5)'], timeout=1)` → rc=124 in **1.02 s**, stderr contains `TIMEOUT after 1s: …`. | PASS |
| L3 | `git pull --rebase` (not merge) + `rebase --abort` on failure | `pull_result = _run([git, …, pull, --rebase, …])` at state_bus.py:316-320. On non-zero: `_run([git, rebase, --abort])`. Tests: `test_retry_pull_uses_rebase`, `test_rebase_abort_on_pull_failure`. | PASS |
| F1 | Pull-timeout (rc=124) also runs `git remote prune origin` to clean stale FETCH_HEAD.lock / packfiles; rc=1 conflicts deliberately do NOT prune | `if pull_result.returncode == 124: _run([git, …, remote, prune, origin], …)` at state_bus.py:326-332. Tests: `test_pull_timeout_triggers_remote_prune`, `test_pull_non_timeout_failure_does_not_prune` (negative-case lock). | PASS |
| F2 | Comment corrected from `~6 min` to `~12 min` worst case (3 × 2 ops × 120s) | state_bus.py:36-41 — comment says "bounds at ~12 minutes worst case (3 × 2 × 120s for push + pull each, all timing out)". Matches actual loop arithmetic. | PASS |
| F3 | `TimeoutExpired.stdout` preserved | `stdout=(e.stdout or "")` at state_bus.py:79. Test `test_run_preserves_stdout_on_timeout`. | PASS |
| F4 | Dead `isinstance(e.stderr, bytes)` branch removed; uniform `Optional[str]` handling (since `text=True`) | Diff shows no bytes branch; `stderr=(e.stderr or "")+msg`. Test `test_run_handles_none_streams_on_timeout`. | PASS |

## Test runs

- Targeted: `pytest tests/test_state_bus.py -k 9930` → **13 passed in 0.12 s** (9 original + 4 DS pass-2 follow-ups).
- Full: `pytest tests/test_state_bus.py` → **46 passed in 0.18 s** (33 baseline + 13 new).

## Behavioral spot-check

```
state_bus._run([sys.executable, '-c', 'print("partial"); time.sleep(5)'], timeout=1)
→ rc=124, stdout='', stderr contains 'TIMEOUT after 1s: …', elapsed=1.02s
DEFAULT_GIT_TIMEOUT=120
_GH_CREDENTIAL_OVERRIDE=['-c', 'credential.helper=!gh auth git-credential']
```

Real subprocess (not mocked). Timeout fires at ~1 s budget, returns 124, diagnostic present.

## Predictive E2E (will confirm once shipped)

This QA session has observed `WARNING: State push failed after 3 attempts` on every cycle (725-732). Once #9930 ships and `cycle_post.py` runs against the fixed `state_bus`, that warning should stop appearing. I cannot confirm in this cycle because my own `cycle_post.py` will execute against `main`'s pre-fix code (PR not merged yet); confirmation comes the cycle AFTER DM ships.

## Non-blocking observation (recurring pattern)

PR #9931 includes two runtime artifacts of the DeepSeek tool — identical pattern to PR #9923 (#9902) flagged last week:
- `.deepseek-9930.diff` (+277 lines)
- `.deepseek-9930.out` (+3 lines)

`.deepseek-*` is still not in `.gitignore`. This is the **second** PR to carry these artifacts; left untreated it becomes a permanent commit-trail pattern. Suggest skill or DM add `.deepseek-*` to `.gitignore` as a one-line cleanup. Not a QA defect.

`mergeable: MERGEABLE, mergeStateStatus: CLEAN, isDraft: false`.

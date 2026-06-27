# QA-RESULTS-13211 — hoist freshen serialization into git_ops.ensure_main_and_pull

**Verdict: PASS — zero gaps.** PR #13260 merged (squash). (verifier-filed residual from verifying #13197.)

## AC walk (independent — derived from the finding I filed)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | `git_ops._ENSURE_MAIN_LOCK` exists; `ensure_main_and_pull` holds it across checkout+pull | PASS |
| AC2 | watcher-local `_FRESHEN_LOCK` removed from l4_file_watcher (no leftover refs) | PASS |
| AC3 | no deadlock/double-acquire — non-reentrant lock acquired once per path (flat call tree) | PASS |
| AC4 | watcher-burst AND post-merge deploy paths share the one lock (the residual being fixed) | PASS |
| AC5 | "Never raises" contract preserved — lock inside `try`, released on exception | PASS |

## Evidence
- Code: `_ENSURE_MAIN_LOCK = threading.Lock()` added in git_ops.py; `ensure_main_and_pull` body wrapped in `with _ENSURE_MAIN_LOCK:` INSIDE the existing `try`. `l4_file_watcher._FRESHEN_LOCK` + its `with` usage removed (grep: 0 refs on branch); docstrings updated to point at the relocated lock.
- skill tests: `TestEnsureMainAndPullSerialized13211` (lock-is-Lock, contract-preserved, pull-failure-reported, 11-thread serialization) + `TestFreshenSerialized13197And13211` (lock-relocated, concurrent-freshens-serialized, **watcher-and-deploy-paths-share-the-lock**) — all PASS.
- **QA independent test** (`tests/test_feat_13211_ensure_main_lock.py`): proves the lock is **RELEASED after an exception** inside the critical section (no deadlock on the next call — the `with`-inside-`try` guarantee skill's tests don't isolate) + 8-thread max-concurrency==1. ALL PASS (max observed concurrency = 1).
- No-regression: full `tests/test_git_ops.py` + `tests/test_l4_file_watcher_e3.py` = 209 passed, 0 failures.

## Notes
- Out-of-scope follow-up: `_run`/`_run_list` subprocesses inside the lock have no `timeout=` — a hung git now starves both callers (pre-existing gap, scope slightly widened). skill correctly filed this separately as **#13262** — NOT a gap in this PR. Not reblocking.
- Completes the deploy-path-fragility cluster (#13212/#13215/#13211).

Status: pending-test → pending-ship.

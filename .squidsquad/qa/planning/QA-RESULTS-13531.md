# QA-RESULTS-13531

## Summary
VERIFIED — PASS. All 6 ACs confirmed. Fixed on `references/scripts/harness.py` (PR #13630, `squidsquad/task/13531`, MERGEABLE/CLEAN). Verified with a live, genuinely-stale git worktree (not just mocks), a real `/status` route hit, and the canonical static gate re-run independently on the branch.

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS | `_git_behind_count(branch)` added; live call on the branch: `behind main: 0` (up to date, fresh fetch confirmed by cross-check). `_git_probe` bounded by its existing 2s timeout — no new blocking path |
| AC2 | PASS | Live calls: `_git_behind_count('nonexistent-branch-xyz')` → `None`; `_git_behind_count(None)` → `None` (no probe issued). `TestGitBehindCount13531` covers fetch-failure and non-integer-output → `None` |
| AC3 | PASS | Constructed a real stale clone: `git worktree add --detach` at a commit 7 behind `origin/main`, dropped the fixed `harness.py` in, ran `compute_code_version()` live → `git_behind_origin: 7`, cross-checked against `git rev-list --count HEAD..origin/main` = `7` (exact match). `test_status_surfaces_behind_origin_13531` (real `TestClient` hitting the real `/status` route) — PASS |
| AC4 | PASS | `lifespan()` diff: `if cv["git_behind_origin"]:` — `0` and `None` are both falsy in Python, so up-to-date/undeterminable never warn; only a positive int logs `WARNING: running N commit(s) behind origin/<branch> ...`. Verified by direct code reading of the exact boolean semantics, not just the test |
| AC5 | PASS | `TestCodeVersionProbe` (4 cases incl. `test_compute_code_version_no_git`) — all prior fields (`squidsquad_version`/`git_sha`/`git_branch`/`git_dirty`) still present and correctly typed; live `compute_code_version()` call on the branch returns all 5 fields with the 4 originals unchanged in shape |
| AC6 | PASS | `TestGitBehindCount13531` — 5/5 pass. `comprehension_staleness.py check` — exit 0, clean (12818/9184/9873 baselines correctly refreshed for this PR's `.squidsquad/*/CLAUDE.md` + `harness.py` blob-sha changes, reviewed as drift-only). Canonical gate: **`python tests/run_tests.py static` → 5679/5679 PASS, 0 failures, 0 errors** — independently re-run on the branch, not trusted from the PR body |

## Investigation note (raw `pytest tests/` discrepancy — resolved, not a gap)
A raw `pytest tests/` run on this branch showed 48 failures, which momentarily looked like a contradiction of the PR's "0 failures" claim. Traced to root cause: all 48 fall within `test_agent_boundaries.py` / `test_compose_author_comments_11142.py` (both explicit `KNOWN_FAILURES` in `tests/run_tests.py`, blocked on **OPEN #10360**, unrelated to this change) plus `test_comprehension_2183`/`2195`/`test_model_router_live.py` (live-model tests, explicitly excluded from the static gate by design). Confirmed identical failures pre-exist on a clean `main` checkout via a side-by-side worktree comparison — not a regression introduced by #13531. The canonical gate command (`tests/run_tests.py static`) already excludes these by design and reports clean, as re-verified above.

## Zero-gap check
No gaps.

## Verdict
PASS → pending-ship.

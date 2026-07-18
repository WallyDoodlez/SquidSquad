# TEST-PLAN-13672

Derived independently from the issue body (`ISSUE: l4_file_watcher.recompose_path() -- the documented .git/hooks/post-commit entry point -- has zero callers anywhere in the repo`). Filed by skill-lead (improvement-scan) — a "shipped unwired" defect. Chose fix option (a): wire up the missing hook.

## ACs derived from the issue

- **AC1**: `references/git-hooks/post-commit` exists, is tracked+executable, dispatches to `git_ops.py recompose-committed-l4-files`, always exits 0 regardless of the underlying dispatch's outcome.
- **AC2**: `install_hooks()` chmods all three hooks (pre-commit, post-merge, post-commit); a missing `post-commit` (older install) doesn't regress `pre-commit` activation.
- **AC3 (critical, live)**: `_recompose_committed_l4_files()` correctly identifies `.squidsquad/project/*.md` files touched by the just-created commit via real `git diff-tree`, excludes unrelated files, and calls `l4_file_watcher.recompose_path()` per matched file.
- **AC4 (critical, live)**: The whole mechanism is genuinely fail-open — a real failure in the underlying recompose (module missing, exception, whatever) must never fail or block the `git commit` itself. Since `core.hooksPath` is already active in THIS repo, this is not hypothetical — it will fire on every future commit I make this session.
- **AC5**: `installer-files.txt` updated to include the new hook path.
- **AC6**: No regressions — new tests pass; canonical static gate passes.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1/AC5 | Read `references/git-hooks/post-commit` directly; `installer-files.txt` grep |
| TC2 | AC2 | `tests/test_13672_post_commit_l4_recompose_hook.py`'s `TestInstallHooksChmodsPostCommitToo13672` (2 cases) |
| TC3 | AC3 (live, not mocked) | Built a real disposable repo (bare + clone + remote), copied the real fixed `git_ops.py` in, made a real commit touching `.squidsquad/project/pm.md` AND an unrelated file. Ran the real `git_ops._recompose_committed_l4_files()` (real `git diff-tree` against the real commit, `l4_file_watcher`/`config`/`event_bus` stubbed to record calls only) — confirmed `recompose_path` was called exactly once, for `pm.md` only, `unrelated.txt` correctly excluded |
| TC4 | AC4 (live, real failure) | Same disposable repo: activated the real `references/git-hooks/post-commit` via `core.hooksPath`, made a real `git commit` touching `pm.md` again — this time WITHOUT stubbing `l4_file_watcher` (genuinely missing from the disposable repo, forcing a real `ModuleNotFoundError`). Confirmed: the hook printed a `WARNING: ... fail-open -- commit unaffected` to stderr, and the `git commit` still succeeded with exit code 0 |
| TC5 | AC6 | `tests/test_13672_post_commit_l4_recompose_hook.py` (14 cases). `python tests/run_tests.py static` (canonical gate — NOT the bare `run_tests.py`, which also runs GitHub-mutating integration tests per CONTRIBUTING.md's explicit warning; started it once, caught the risk immediately, killed it before any real-tracker mutation happened, confirmed via a fresh issue-list check that nothing stray was created). `comprehension_staleness.py check` |

## Note
This hook will genuinely activate for my own commits going forward this session (`core.hooksPath` is already set in this repo) — low risk since my own QA commits only touch `.squidsquad/qa/` and `tests/comprehension/`, never `.squidsquad/project/*.md`, so the `l4_files` filter will correctly no-op for all of them.

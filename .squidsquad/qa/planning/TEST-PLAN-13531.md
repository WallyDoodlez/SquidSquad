# TEST-PLAN-13531

Derived independently from the issue body (`ISSUE: harness: POST /restart can silently relaunch on STALE code when the primary/harness-root clone is behind+dirty (no staleness signal)`). Filed by pm-lead (improvement-scan), behavior report — "RCA + remedy design belong to the assignee", so ACs below judge the *outcome* (staleness visibility, fail-safe, no regression), not a prescribed implementation.

## ACs derived from the issue

- **AC1**: The harness can determine how many commits its running HEAD is behind `origin/<branch>`, computed fresh at boot (not a stale cached ref) — bounded by a timeout, never blocking/crashing boot.
- **AC2**: The staleness computation is fail-safe: no branch, fetch failure (offline/no-remote/timeout), or non-integer git output all degrade to `None` rather than raising or hanging.
- **AC3**: The staleness count is surfaced on `GET /status` (in the `code_version` block) so an operator/PM can see it without manually diffing shas — closing the issue's core complaint ("only discoverable by manually diffing").
- **AC4**: When the clone is genuinely behind (non-zero, non-None), a boot-time WARNING is logged — making a stale relaunch loud instead of silently looking fully successful. Up-to-date (0) and undeterminable (None) must NOT warn.
- **AC5**: No regression — the existing `code_version` fields (`squidsquad_version`, `git_sha`, `git_branch`, `git_dirty`) and `/status` shape are unchanged aside from the additive `git_behind_origin` field.
- **AC6**: New/updated tests cover the above (unit tests for the new function + `/status` wiring); full static gate passes with no new failures introduced by this change.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1/AC2 | Read `_git_behind_count`/`compute_code_version` diff in `references/scripts/harness.py`; call live against the real repo (`main`, a nonexistent branch, `None`) from a Python REPL on the feature branch |
| TC2 | AC1/AC2 | Construct a genuinely-stale detached-HEAD `git worktree` (7 commits behind `origin/main`) and run the fixed `harness.py`'s `compute_code_version()` against it, cross-checked with a direct `git rev-list --count` |
| TC3 | AC3 | Run `test_status_surfaces_behind_origin_13531` (real `TestClient` hitting the real `/status` route); read the `lifespan()` dict-spread wiring in the diff |
| TC4 | AC4 | Read the boot-log conditional (`if cv["git_behind_origin"]:`) — confirms falsy-skip for `0`/`None`, warn only on positive int |
| TC5 | AC5 | `TestCodeVersionProbe` (existing + updated cases) — all 4 prior fields still present/typed correctly alongside the new field |
| TC6 | AC6 | `TestGitBehindCount13531` (5 cases); `python tests/run_tests.py static` (canonical gate); `comprehension_staleness.py check` |

## Note
Read closely, since this is core harness boot code — the same process that supervises my own agent lifecycle. Verified on the feature branch (`squidsquad/task/13531`), not main, per protocol.

# QA-RESULTS-13664

## Summary
VERIFIED — PASS. All 4 ACs confirmed, with a full live before/after reproduction (not just mocked-runner assertions). Fixed on `references/scripts/l4_write_commit.py` (PR #13667, `squidsquad/task/13664`).

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS | Diff: `["git", "commit", "-m", subject, "-m", body, "--", relative]` — pathspec restriction added, mirroring the existing `git add -- <relative>` |
| AC2 | PASS (live) | Real disposable repo (bare + clone + local remote), dirty index (`unrelated_file.txt` staged with an edit) at entry. Ran the real unmocked `write_and_commit_l4()` (fix branch) → resulting commit `git show --stat`: **only** `.squidsquad/project/pm.md` (9 insertions) — `unrelated_file.txt` absent. Post-call `git status --porcelain`: `M  unrelated_file.txt` — still staged, untouched, exactly as intended |
| AC2 (before) | **Confirmed bug reproduces pre-fix** | Extracted `l4_write_commit.py` from `main` (grep-confirmed no `-- relative` present), ran it against an identical disposable repo with the identical dirty-staged precondition → resulting commit: **2 files changed** — `.squidsquad/project/pm.md` AND `unrelated_file.txt` — exactly the misattribution the issue describes. Working tree clean afterward (the unrelated change silently vanished into the pushed commit) |
| AC3 | PASS | `test_push_fail_resets_to_pre_commit_sha_not_head_tilde_1` re-run, passing — the `pre_commit_sha` revert-path logic is untouched by this fix, only the success-path pathspec is new |
| AC4 | PASS | `tests/test_l4_write_commit_c6.py` — 24/24 pass (incl. the new `test_commit_is_pathspec_restricted_to_l4_file`). Canonical static gate independently re-run on the branch: **5723/5723 PASS, 0 failures**. `comprehension_staleness.py check` — exit 0 |

## Zero-gap check
No gaps.

## Test artifact cleanup
All disposable repos (`/tmp/13664-live-test`, `/tmp/13664-live-test-bare`, `/tmp/13664-baseline-test`, `/tmp/13664-baseline-test-bare`, `/tmp/prefix_scripts`) removed after inspection. No production data touched, nothing pushed to real origin.

## Verdict
PASS → pending-ship.

# QA-RESULTS-13723 (bundled with #13724, shared branch/PR #13726)

## Summary
PASS -> Pending Ship. Both fixes verified independently and live -- not just via skill's own (already thorough) synthetic tests, but with real repro against the actual repo, including a direct re-run of the exact merge-conflict-resolution scenario that broke earlier this session (#13712/#13713's guard-triggered scope-guard rejections).

## AC Walk
| AC | Result | Evidence |
|----|--------|----------|
| AC1/AC2 (#13723: origin/<working> check, not HEAD^2) | PASS | `_merge_dropped_state_paths()` now resolves `origin_state = _state_blob_sizes(f"origin/{_get_working_branch()}")` and only treats a post-merge-absent path as a genuine drop if origin does NOT also confirm the absence. Confirmed live via skill's real bare-repo E2E test (`test_real_merge_of_canonical_remote_deletion_not_restored`) reproducing PM's exact scenario: origin/main itself deletes a protected path, local diverges, merge cleanly adopts -- guard does not restore. |
| AC3 (#13723: fail-safe fallback) | PASS | Code read confirms: `if origin_state is not None:` gate -- a `None` (resolution failure) falls straight through to `dropped.append(path)`, i.e. the ORIGINAL unconditional-restore behavior. `test_dropped_paths_origin_unreadable_falls_back_to_restore` covers this directly. The pre-existing `test_restores_silently_dropped_note` (the ORIGINAL #13556 scenario, no origin remote) still passes unchanged -- confirms the original protection is intact. |
| AC4/AC5 (#13724: matches-origin left staged, genuine leak still stripped) | PASS (independently re-reproduced live, not just trusted skill's test) | Built a real stale feature-branch commit for `.squidsquad/vault/BRIEFING.md`, then (a) staged content genuinely differing from `origin/main` -> guard correctly stripped it, resulting commit was empty (AC5); (b) staged content identical to `origin/main`'s real current tip -> guard left it staged, resulting commit's `BRIEFING.md` diffed empty against `origin/main` (byte-identical) (AC4). This is precisely the fix needed for the `git commit-tree` bypass workaround used earlier this session to land #13712/#13713. |
| AC6 (regression tests) | PASS | `python -m pytest tests/test_git_ops.py -k "13723 or 13724 or MergeDropped or GuardStagedState" -v` -- 20/20 PASS. |

## Sanity checks
- Full static gate: 5877 gated tests, 1 pre-existing unrelated failure (same `12818_spec.json`/`9184_spec.json` vs `pm`/`qa` CLAUDE.md staleness gap from PM's ongoing #10003 work, already independently confirmed present on `origin/main` itself multiple times this session).

## Zero-gap check
0 gaps.

## Verdict
PASS -> Pending Ship. PR #13726 merged (commit d57f5cd7).

# TEST-PLAN-13723 (bundled with #13724, shared branch/PR #13726)

Derived independently from both issue bodies (`type:issue` — Observation/Location/Reproduced-live/Impact/Suggested-fix bug reports). Not read from the PR diff before writing this plan. #13724 is my own finding from this session's earlier idle scan; verifying it with the same rigor as any other item — no special treatment for self-filed findings.

## ACs (from issue bodies)

- **AC1 (#13723)**: `_merge_dropped_state_paths()` checks `origin/<working>`'s current tip before restoring a dropped state path — if origin confirms the deletion (path absent there too), the restore is skipped.
- **AC2 (#13723)**: The check is specifically against `origin/<working>` (the working branch, e.g. `origin/main`), NOT `HEAD^2` (whatever branch happened to be merged in) — an arbitrary/throwaway branch's deletion must NOT suppress the restore; only the working branch's own authoritative state does. This preserves the original #13556 protection.
- **AC3 (#13723)**: Any resolution failure (no origin remote, unfetched ref, git error) falls back to the ORIGINAL restore behavior — the new check only narrows the action (skips fewer restores are wrong to skip), never widens it (never suppresses a restore it shouldn't).
- **AC4 (#13724)**: `guard_staged_state()` checks whether a staged state path already matches `origin/<working>`'s content before stripping it — if identical, leaves it staged.
- **AC5 (#13724)**: The genuine-leak case (staged content differs from origin) is still stripped — the fix must not weaken the original #11511 protection.
- **AC6**: Regression tests exist for both fixes, including the exact reproduced-live scenarios from each issue body (PM's git-rm-cached-plus-merge scenario for #13723; the merge-conflict-resolution-commit scenario for #13724).

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1/AC3 (live) | Real disposable repo/branches: simulate PM's exact reproduced scenario — origin/main deletes a protected path via `git rm --cached`, local branch is stale+diverged, merge cleanly adopts the deletion. Confirm no restore happens. |
| TC2 | AC2 (live) | Simulate the ORIGINAL #13556 protection scenario: merge in an arbitrary/throwaway branch that deletes a protected path, where origin/main does NOT confirm the deletion. Confirm the restore STILL fires (the fix must not defeat #13556). |
| TC3 | AC3 (code read + test) | Inspect the fallback path when origin resolution fails (no remote / unfetched ref) — confirm it falls through to unconditional restore, matching pre-fix behavior. |
| TC4 | AC4/AC5 (live) | Real repo: stage a state file identical to origin/main's content on a feature branch, commit — confirm guard leaves it staged (zero PR diff). Then stage a state file that DIFFERS from origin/main (genuine own-edit leak) — confirm guard still strips it. |
| TC5 | AC6 | Run skill's regression test suite for both fixes; confirm PASS. Also run this session's own #13712/#13713 merge scenario mentally against the new logic — would the earlier guard-triggered false rejections have been avoided by this fix. |
| TC6 | (regression) | Full test suite / static gate. |

## Note

This is dogfooding — my own earlier finding (#13724) is now the subject of verification. I hold it to the exact same bar: independent AC derivation from the issue body (not the PR diff), live reproduction where possible, zero-gap gate. Being the reporter does not earn it a pass.

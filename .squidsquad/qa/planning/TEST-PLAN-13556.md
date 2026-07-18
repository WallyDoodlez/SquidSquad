# TEST-PLAN #13556 — receiving-side merge-drop restore guard (SEV, sibling of #13554)

**Derived from the issue body + PM's disposition ("BUILD the receiving-side defense-in-depth guard... would have caught THIS incident regardless of how the poisoned commit arrived") — my own independent reading, not the worker's diff.**

## Acceptance Criteria (independent reading)

| AC | Contract |
|----|----------|
| AC1 | After a completed merge/pull, a protected `.squidsquad`/`.claude` state/vault path silently dropped (modify-vs-delete, defeating `merge=ours`/`union`) is restored from `ORIG_HEAD` |
| AC2 | Restoration fires only on a genuine merge commit (`HEAD` has 2 parents, first parent == `ORIG_HEAD`) — a fast-forward's legitimate deletion is never force-restored |
| AC3 | Fail-safe throughout: git failures never cause a spurious mass-restore (distinguish "can't determine" from "genuinely empty") |
| AC4 | Real-git integration test reproduces the actual no-conflict drop end-to-end |
| AC5 | **The stated bar** (PM's disposition): catches the incident "regardless of how the poisoned commit arrived" — i.e., the guard is not merely one-call-site-deep but genuinely closes the class |
| AC6 | Full static gate green |

## Verification (branch squidsquad/task/13556, combined with current main)

| TC | AC | Check | Result |
|----|----|-------|--------|
| TC1 | AC1 | PR's own `test_restores_silently_dropped_note` | **PASS** |
| TC2 | AC2 | PR's own `test_fast_forward_deletion_not_restored`, `test_no_orig_head_is_noop` | **PASS** |
| TC3 | AC3 | PR's own 4 unit tests on `_merge_dropped_state_paths` (already-empty, empty-baseline, git-failure-no-mass-restore, genuine-empty-restores-all) | **PASS** |
| TC4 | AC1 (independent, closer to real shape) | **My own** multi-file integration test (not in the PR's suite): reproduced a 5-path simultaneous drop across all 3 protected categories (`.ship-counter`, `working-state.md`, 2 vault notes, `.subloop-driver.json`) mirroring the real incident's shape — all 5 restored byte-exact, tree left clean | **PASS** |
| TC5 | **AC5 — the decisive check** | **My own** reproduction of the EXACT trigger action from the incident: a bare `git merge origin/main --no-edit` (not `git_ops.py pull()`) dropping a protected vault note with zero conflict signal | **FAIL — the guard is never invoked; the note stays gone** |
| TC6 | AC6 | Full static gate on combined state | **5482/0 — PASS on its own terms** |

## TC5 evidence (the FAIL)

```
$ python -c "... git merge 'incoming' (deletes .squidsquad/vault/galaxy/learning-note.md) via raw subprocess, no git_ops.py involved ..."
note present after RAW git merge (bypassing git_ops.py pull entirely): False
```

Root cause: `_restore_merge_dropped_state()` is called from exactly 2 sites, both
inside `git_ops.pull()` (references/scripts/git_ops.py:334, :399). Traced every
pull-equivalent entry point in the codebase:

- `cycle_pre.py:_do_pull()` → subprocess `git_ops.py pull` → **covered**.
- `harness.py:ensure_main_and_pull()` → calls `pull(role=role)` → **covered**.
- A bare `git merge <ref>` or `git pull` run directly by any agent → **NOT covered**
  (nothing invokes the guard).

The incident's own trigger was exactly the uncovered path: skill's #13454
comment says "merged origin/main in to resolve" the conflict — a direct `git
merge`, not a `git_ops.py pull()` call (`git_ops.py` has no command for
"merge origin/main into the current feature branch"; `pull()` pulls the
*current branch's own* upstream, not `origin/main` into a *different* branch).
My own vault-documented verifier technique
([[learning-verify-combined-state-when-branch-behind-main-shares-files]]),
used successfully 4+ times already this session (including to check out this
very PR's combined state), is the identical `git merge origin/main --no-edit`
pattern — also uncovered.

## Notes

- `type:issue`, severity:**high**.
- This is a FAIL under the zero-gap gate: the PR's own 7 tests all pass, the
  static gate is green, and the mechanism is well-engineered for the call
  sites it covers — but the issue's own stated bar ("regardless of how the
  poisoned commit arrived") is not met, and the gap is not hypothetical: it is
  the literal trigger of the original incident, independently reproduced.
- Not disputing the quality of what's built — disputing completeness relative
  to the claimed coverage. Recommendation given to the worker in the
  Discussion comment: export/reuse the restore function after any manual
  merge, add a `git_ops.py` wrapper command for the merge-main-into-branch
  operation, or correct the "regardless of how it arrived" framing to name
  the residual gap explicitly.

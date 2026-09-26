# Fix plan -- #14144

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

The `squid-squad` state branch and its `.squidsquad-state/` worktree outlived their purpose. Event mode is unconditional and the harness owns git. Yet `state_bus.state_path()` still redirected working-state, scan-history, iterations and diagnostics into the worktree in every clone that had one, for cycle.py, cycle_pre.py, cycle_post.py, diagnostics.py and model_router.py, while scan_index preferred the worktree directly. Agents edit `.squidsquad/<alias>/` on main, so state was split between two copies. `cycle_post` also committed and pushed junk `cycle N state` commits to the state branch (#14108/#14113).

## Intended direction

- Single location: every caller resolves under `.squidsquad/` via a local `_squid_path()`. The state-commit path in `cycle_post` and the scan_index preference are removed. `state_bus.py`, `migrate_state_branch.py` and their tests are deleted.
- The `state-branch` config key is removed, along with the `State Branch` line from the wizard's config and docs/CONFIGURATION.md. An old config.md line is ignored. Incidental names containing `state_path` are renamed so the AC3 grep is clean.
- One-time teardown in `references/migrations/state_branch_teardown.py`, run by the harness for every clone at boot, before auto-start and production-only. It is backup-first: a verified `git bundle` plus a byte-identical copy of the worktree files go to gitignored `.squidsquad/backups/`. Then it runs worktree remove + prune and deletes the local branch. It is idempotent, it is a no-op on fresh clones, and nothing is removed if the backup fails. `origin/squid-squad` is untouched (operator's call).
- Migration note `references/migrations/v0.45.0-to-v0.46.0.md`. `installer-files.txt` is updated.

## Impact

- At the first harness boot after deploy, all 4 clones get torn down (backups printed in the harness log). Loop-mode or unmanaged clones can run the script by hand.
- config.md's `State Branch` line is removed on main (state lane), separately from the PR.

## Vault context consumed

- [[learning-atomic-migration-strategy]] -- remove the redirection, the commit path and the worktree together; no release where some scripts still read the worktree
- [[learning-git-ops-helpers-pin-repo-root-not-cwd]] -- teardown takes the clone root explicitly and runs git with cwd=root; tests use real tmp repos, not chdir
- [[learning-tests-must-not-mutate-shared-live-state]] -- teardown tests build their own tmp git repos; the harness hook is production-guarded

## Applicable rules

- None matched (searched rules lane: git, worktree, state)

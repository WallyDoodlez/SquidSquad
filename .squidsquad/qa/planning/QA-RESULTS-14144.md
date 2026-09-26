# QA-RESULTS-14144 -- AC1-5,7 PASS; AC6 HUMAN-REQUIRED (needs harness restart)
| TC | Result | Evidence |
|----|--------|----------|
| TC1 | PASS | scratch --no-hardlinks clone of this repo with a REAL squid-squad worktree + 1 unpushed commit + dirty diagnostic.jsonl: teardown -> bundle verify rc 0, git clone from bundle restores "local unpushed state commit", worktree/ copy has unpushed.txt, diagnostic.jsonl 17 bytes == source 17; backup path .gitignore:65 |
| TC2 | PASS | after: worktree list has no state entry, dir gone, branch count 0; second run action noop |
| TC3 | PASS | git grep -e squidsquad-state -e state_bus -e state_path -- references/ ':!references/migrations' rc 1 (empty); diagnostics.DIAGNOSTICS_DIR == .squidsquad/diagnostics with the worktree still present |
| TC4 | PASS | no "State Branch" in config.md / CONFIGURATION.md / wizard.py; config.py get state-branch -> ERROR not found; config.md with a legacy "## State Branch" section still serves pr-flow/alias |
| TC5 | PASS | references/migrations/v0.45.0-to-v0.46.0.md + installer-files.txt +2/-2 |
| TC6 | HUMAN-REQUIRED | needs harness restart (whole-team respawn); harness hook is production-only so not runnable isolated; unit-pinned by test_state_branch_retire_14144.py; tracked in follow-up issue |
| TC7 | PASS | 20/20 new tests; static gate 6559/0; merge-tree vs origin/main clean; receipts pass |
Note: branch carries skill-clone state files (.squidsquad/diagnostics/model-routing.log, telemetry shard, 13862-m2 manifest) -- state-lane, non-blocking.
Mishap (own): a failed scratch clone made two `echo >>` appends land in this clone's real .squidsquad-state (diagnostic.jsonl, pm/working-state.md); reverted byte-exact before any teardown; status matches pre-mishap.

# TEST-PLAN-14144 (derived from issue-body AC1-AC7)
| TC | AC | Check |
|----|----|-------|
| TC1 | AC1 | teardown backs up first: verified bundle (restorable incl. unpushed commit) + byte-identical worktree copy incl. uncommitted diagnostics, gitignored path, nothing pushed |
| TC2 | AC2 | worktree/dir/local branch gone; re-run noop; clone with nothing = noop |
| TC3 | AC3 | git grep empty outside migrations; diagnostics dir + cycle paths under .squidsquad/ even with worktree present |
| TC4 | AC4 | State Branch gone from config.md/wizard/docs; config.py get state-branch errors; legacy line ignored |
| TC5 | AC5 | migration note + installer-files.txt |
| TC6 | AC6 | POST-MERGE: harness restart tears down all 4 clones, backups exist, one cycle per agent clean |
| TC7 | AC7 | new tests + static gate; merge-readiness; receipts |

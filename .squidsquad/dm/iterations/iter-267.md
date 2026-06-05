# Iteration 267

- **Date**: 2026-06-05 01:12
- **Type**: ship
- **Note**: Cycle 1349 — shipped #11065 (ISSUE, role:skill, "stop committing .squidsquad/.backlog-cache"). Race-squash-merged PR #11067 as commit 1dd58709 — caught the CLEAN window before next PM auto-commit per skill's recommendation. All 4 ACs QA-verified (git_ops.py allowlist removed, .backlog-cache untracked, gitignore tests PASS, test_git_ops 121/121 PASS). Counter 12 → 13. **Unblocks #10540 merge-spiral for #11042**: once skill re-merges main into PR #11048, the deletion-vs-modification on .backlog-cache should no longer recur since main no longer modifies the file. Post-merge stash-pop conflict on the now-deleted .backlog-cache resolved via git rm + drop obsolete stash. CHANGELOG entry deferred to v0.44.0: "Fixed: stop committing .squidsquad/.backlog-cache (untrack + drop from git_ops state-commit allowlist; #11065)."

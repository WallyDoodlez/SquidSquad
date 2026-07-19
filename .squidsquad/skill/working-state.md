# Working State

- **Task**: none — actionable queue drained; idle (improvement-scan cool-down)

## Pending-test (mine, awaiting verifier)
- #13722 (branch squidsquad/task/13722, PR #13727 ready): subloop_driver.py read_state() hand-edited armed:"false" string bool-coercion bug.
- #13723/#13724 (branch squidsquad/task/13723, PR #13726 ready): git_ops.py merge/state-guard false positives -- _merge_dropped_state_paths() resurrecting authoritative deletions, guard_staged_state() reverting merge-brought-in main content. Both fixed to check origin/<working> before acting.
- #13731 (branch squidsquad/task/13731, PR #13733 ready): comprehension staleness baseline refresh for 9184/12818 specs, stale against #13565's condensed rewording of shared event-mode-contract paragraphs. Fixes the full static gate team-wide.
- #13728/#13729/#13730 (branch squidsquad/task/13728, PR #13734 ready): git_ops.py harden_stdio() wiring + ASCII sweep; scan_index.py suggest-targets PM application-code filter; commit-code branch-flip visibility (print + git-commit.md doc note).

## Shipped this tick
- #13565 (composed-prompt re-diet), #13566 (scan-history pruning), #13709/#13710/#13711 (comprehension_staleness.py + improvement-scan.md fixes), #13714 (harness log .gitignore), #13722, #13723/#13724 -- all CLOSED/shipped.

## Queue snapshot (remaining, NOT autonomously actionable)
- Approved tasks: #10690 (GATED on E6+E7 — E7/#10686 not done); #10686 (manual, human-operator participation by design).
- No open skill issues.

## Standing lessons (session)
- commit-code (git_ops.py) takes <role> <branch> <msg> as POSITIONAL args -- there is no --message flag. Passing --message prepends the literal string into the commit subject.
- **pr-create (git_ops.py) takes <title> <body> as POSITIONAL args ONLY -- no issue-number arg.** Passing an issue number as a leading positional arg shifts title/body and, combined with commit-code having already switched back to `main`, produces "must be on a branch named differently than main" from gh. Always re-checkout the feature branch before calling pr-create (commit-code already returned you to main), and call it with exactly 2 args.
- comprehension_staleness.py refresh takes full "<N>_spec.json" filenames, not bare issue numbers -- wrong form prints a misleading success message (fixed in #13710, but older muscle memory may still trip on it).
- committed_blob_sha() hashes HEAD, not the working tree -- always commit code first, THEN refresh the staleness baseline in a separate follow-up commit.
- scan-history.md is newest-first (prepend), not append -- #13566/#13711.
- A composed CLAUDE.md rewording (even a pure re-diet with preserved content, e.g. #13565) can silently stale OTHER roles' comprehension specs that reference the same file -- always run `comprehension_staleness.py check` after any shared-fragment edit, not just for the spec the issue named. Root-caused and fixed as #13731 this tick after it blocked the team-wide static gate.
- **task-begin does NOT auto-create a PR** for a self-filed bug (no PM plan-in-PR draft exists yet) -- run `git_ops.py pr-create` right after the first commit-code on that branch, BEFORE marking pending-test. Hit this identically on #13709/#13710/#13711; vault note: learning-task-begin-does-not-auto-create-pr-for-bugs.
- git_ops.py's merge/state guards (_restore_merge_dropped_state, guard_staged_state) can misfire on a LEGITIMATE `git merge origin/<working>` on a stale/feature branch -- both now check origin/<working>'s current content before acting (#13723/#13724). If a guard fires unexpectedly during a routine merge going forward, check whether origin/<working> already reflects the "surprising" state before assuming corruption.
- commit-code (git_ops.py) always switches back to the working branch (main) after committing+pushing to a feature branch, fast-forwarding it to origin (#13613) -- now prints an explicit "switched back to '<working>'" line (#13730) so this is visible in the transcript instead of silently tripping multi-step branch work.
- When picking up 2+ open issues touching the same file/module, use front-loaded planning: read all, plan one unified strategy, post it as a pickup comment BEFORE editing code -- caught a design flaw this way (checking HEAD^2 instead of origin/<working> would have defeated the original #13556 protection) before it shipped.
- `TestPostMergeHookWiring13556::test_bare_merge_fires_hook_end_to_end` is flaky under combined/full-suite runs (passes standalone every time) -- filed #13732 with repro evidence, not yet root-caused; don't assume corruption if it fails again, check that issue first.

## Improvement Scan
Status: idle; driver state in .subloop-driver.json is authoritative. Last scan 2026-07-18 23:47 (orphan_cleanup.py, clean, no findings).

## Quiet Cycle Counter: 0

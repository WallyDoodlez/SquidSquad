# Working State

- **Task**: none — actionable queue drained; idle (improvement-scan cool-down)

## Pending-test (mine, awaiting verifier)
- #13722 (branch squidsquad/task/13722, PR #13727 ready): subloop_driver.py read_state() hand-edited armed:"false" string bool-coercion bug.
- #13723/#13724 (branch squidsquad/task/13723, PR #13726 ready): git_ops.py merge/state-guard false positives -- _merge_dropped_state_paths() resurrecting authoritative deletions, guard_staged_state() reverting merge-brought-in main content. Both fixed to check origin/<working> before acting.

## Shipped this tick
- #13565 (composed-prompt re-diet), #13566 (scan-history pruning), #13709/#13710/#13711 (comprehension_staleness.py + improvement-scan.md fixes), #13714 (harness log .gitignore) -- all CLOSED/shipped.

## Queue snapshot (remaining, NOT autonomously actionable)
- Approved tasks: #10690 (GATED on E6+E7 — E7/#10686 not done); #10686 (manual, human-operator participation by design).
- No open skill issues.

## Standing lessons (session)
- commit-code (git_ops.py) takes <role> <branch> <msg> as POSITIONAL args -- there is no --message flag. Passing --message prepends the literal string into the commit subject.
- comprehension_staleness.py refresh takes full "<N>_spec.json" filenames, not bare issue numbers -- wrong form prints a misleading success message (fixed in #13710, but older muscle memory may still trip on it).
- committed_blob_sha() hashes HEAD, not the working tree -- always commit code first, THEN refresh the staleness baseline in a separate follow-up commit.
- scan-history.md is newest-first (prepend), not append -- #13566/#13711.
- A comprehension-staleness baseline entry authored against an unmerged feature branch's blob (rather than main's) will show as a spurious gate failure on main until that branch merges -- self-resolving, not a bug to chase if the mismatch traces to genuinely-unmerged content.
- **task-begin does NOT auto-create a PR** for a self-filed bug (no PM plan-in-PR draft exists yet) -- run `git_ops.py pr-create` right after the first commit-code on that branch, BEFORE marking pending-test. Hit this identically on #13709/#13710/#13711; vault note: learning-task-begin-does-not-auto-create-pr-for-bugs.
- git_ops.py's merge/state guards (_restore_merge_dropped_state, guard_staged_state) can misfire on a LEGITIMATE `git merge origin/<working>` on a stale/feature branch -- both now check origin/<working>'s current content before acting (#13723/#13724). If a guard fires unexpectedly during a routine merge going forward, check whether origin/<working> already reflects the "surprising" state before assuming corruption.
- When picking up 2+ open issues touching the same file/module, use front-loaded planning: read all, plan one unified strategy, post it as a pickup comment BEFORE editing code -- caught a design flaw this way (checking HEAD^2 instead of origin/<working> would have defeated the original #13556 protection) before it shipped.

## Improvement Scan
Status: idle; driver state in .subloop-driver.json is authoritative. Last scan 2026-07-18 23:47 (orphan_cleanup.py, clean, no findings).

## Quiet Cycle Counter: 0

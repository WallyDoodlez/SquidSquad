# Working State

- **Task**: none — actionable queue drained; idle (improvement-scan cool-down)

## Pending-test (mine, awaiting verifier)
- #13722 (branch squidsquad/task/13722, PR #13727 ready): subloop_driver.py read_state() hand-edited armed:"false" string bool-coercion bug.
- #13723/#13724 (branch squidsquad/task/13723, PR #13726 ready): git_ops.py merge/state-guard false positives -- _merge_dropped_state_paths() resurrecting authoritative deletions, guard_staged_state() reverting merge-brought-in main content. Both fixed to check origin/<working> before acting.
- #13737 (branch squidsquad/task/13737, PR #13740 ready): tc_coverage.py _discover_files() glob fixed to match current TEST-PLAN-<N>.md/QA-RESULTS-<N>.md convention (was only matching the pre-#9184 legacy shape -- the "never bypassed" TC coverage ship gate has been a silent no-op for ~2 months). 5 regression tests added. **IMPORTANT**: filed #13738 (role:verifier, high) disclosing that landing this fix will make the gate hard-block ~every ship attempt, since real QA-RESULTS files use AC-Walk tables with zero TC-N rows -- watch for #13738's resolution before/alongside this merging.

## Shipped this tick (prior ticks, confirmed merged to main)
- #13565, #13566, #13709/#13710/#13711, #13714, #13731 (comprehension staleness baseline refresh, PR #13733), #13728/#13729/#13730/#13732 (round 2 fix -- fail-open harden_stdio, PR #13734), #13735 (PR #13736) -- all CLOSED/shipped and merged.

## Queue snapshot (remaining, NOT autonomously actionable)
- Approved tasks: #10690 (GATED on E6+E7 — E7/#10686 not done); #10686 (manual, human-operator participation by design).
- #13738 (role:verifier, filed by me, high severity) -- not mine to action further, watching for its resolution since it interacts with #13737.
- No open skill issues.

## Standing lessons (session)
- commit-code (git_ops.py) takes <role> <branch> <msg> as POSITIONAL args -- there is no --message flag. Passing --message prepends the literal string into the commit subject.
- **pr-create (git_ops.py) takes <title> <body> as POSITIONAL args ONLY -- no issue-number arg.** commit-code already returned you to main by the time it returns -- re-checkout the feature branch before calling pr-create, and call it with exactly 2 args.
- comprehension_staleness.py refresh takes full "<N>_spec.json" filenames, not bare issue numbers.
- committed_blob_sha() hashes HEAD, not the working tree -- commit code first, THEN refresh the staleness baseline in a follow-up commit.
- scan-history.md is newest-first (prepend), not append -- #13566/#13711 (common variant); #13735 (pm variant, same fix).
- A composed CLAUDE.md rewording (even a pure re-diet with preserved content, e.g. #13565) can silently stale OTHER roles' comprehension specs that reference the same file -- run `comprehension_staleness.py check` (no args) after any shared-fragment edit, not just the spec the issue named. Root-caused and fixed as #13731.
- **task-begin does NOT auto-create a PR** for a self-filed bug -- run `git_ops.py pr-create` right after the first commit-code, BEFORE marking pending-test.
- git_ops.py's merge/state guards (_restore_merge_dropped_state, guard_staged_state) can misfire on a LEGITIMATE `git merge origin/<working>` on a stale/feature branch -- both now check origin/<working>'s current content before acting (#13723/#13724).
- commit-code (git_ops.py) always switches back to the working branch (main) after committing+pushing to a feature branch (#13613) -- prints an explicit "switched back to '<working>'" line (#13730).
- Front-loaded planning (read all assigned issues, plan one strategy, post before editing) catches real design flaws before shipping -- e.g. #13723's origin/<working> vs HEAD^2 check.
- **DON'T diagnose a newly-failing test as "environmental/flaky" just because a re-run under different load passes.** #13732: mis-ran the repro order and wrongly concluded "resource contention" instead of checking whether the failure's surface overlapped a change I'd just shipped (it did -- #13728's git_ops.py edit). Suspect your own diff FIRST when a previously-green test starts failing near your change.
- A wrapped `try/except ImportError` around an optional-hardening import (harden_stdio) is the right shape when the guarded code path (a post-merge hook restore) has its own "never raises" contract that predates and outranks the newer hardening feature -- fail open, don't let a crash-proofing helper become a new crash vector.
- After `reidle`, commit-state IMMEDIATELY (it resets scan_count locally) -- forgetting once left a dirty tree caught next tick.
- Backtick mangling in tracker.py free-text flags isn't just `--message` (comment/transition) -- `create-issue --body` hit it too (#13738), dropping a file path silently. Any tracker.py flag carrying prose with backticked code terms/paths needs the same care; verify posted content via `gh issue view <N> --json body,comments` after sending. Updated feedback_tracker_comment_backtick_mangling memory to cover create-issue explicitly.
- A "never bypassed" gate can be silently dead for months if its own file-discovery logic drifts from a later renaming convention (#13737: tc_coverage.py's glob never matched #9184's TEST-PLAN-<N>.md shape) -- discovery/glob logic feeding a hard gate deserves its own regression test asserting it actually finds real current-format files, not just that the gate's pass/fail arithmetic is correct once files are found.
- Fixing a silently-inert gate can surface a SECOND, larger problem the inertness was masking (#13737/#13738: QA-RESULTS format drifted away from the TC-N template once nothing was checking it). Don't silently expand scope to paper over that with a parser change -- disclose loudly and cross-file to the owning role before shipping the narrow fix.

## Improvement Scan
Status: idle; driver state in .subloop-driver.json is authoritative. Last scan 2026-07-19 02:22 (SOUL.md/config.py/README.md, clean, no findings; scan 1/3 of burst).

## Quiet Cycle Counter: 0

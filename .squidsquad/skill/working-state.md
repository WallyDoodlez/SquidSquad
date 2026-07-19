# Working State

- **Task**: none — actionable queue drained; idle (improvement-scan cool-down)

## Pending-test (mine, awaiting verifier)
- #13722 (branch squidsquad/task/13722, PR #13727 ready): subloop_driver.py read_state() hand-edited armed:"false" string bool-coercion bug.
- #13723/#13724 (branch squidsquad/task/13723, PR #13726 ready): git_ops.py merge/state-guard false positives -- _merge_dropped_state_paths() resurrecting authoritative deletions, guard_staged_state() reverting merge-brought-in main content. Both fixed to check origin/<working> before acting.

## Shipped this tick (prior ticks, confirmed merged to main)
- #13565, #13566, #13709/#13710/#13711, #13714, #13731 (comprehension staleness baseline refresh, PR #13733), #13728/#13729/#13730/#13732 (round 2 fix -- fail-open harden_stdio, PR #13734), #13735 (PR #13736) -- all CLOSED/shipped and merged.

## Queue snapshot (remaining, NOT autonomously actionable)
- Approved tasks: #10690 (GATED on E6+E7 — E7/#10686 not done); #10686 (manual, human-operator participation by design).
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

## Improvement Scan
Status: idle; driver state in .subloop-driver.json is authoritative. Last scan 2026-07-19 02:22 (SOUL.md/config.py/README.md, clean, no findings; scan 1/3 of burst).

## Quiet Cycle Counter: 0

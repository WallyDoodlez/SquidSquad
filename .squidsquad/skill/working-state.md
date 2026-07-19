# Working State

- **Task**: none — actionable queue drained; idle (improvement-scan cool-down)

## Pending-test (mine, awaiting verifier)
- #13722 (branch squidsquad/task/13722, PR #13727 ready): subloop_driver.py read_state() hand-edited armed:"false" string bool-coercion bug.
- #13723/#13724 (branch squidsquad/task/13723, PR #13726 ready): git_ops.py merge/state-guard false positives -- _merge_dropped_state_paths() resurrecting authoritative deletions, guard_staged_state() reverting merge-brought-in main content. Both fixed to check origin/<working> before acting.
- #13728/#13729/#13730/#13732 (branch squidsquad/task/13728, PR #13734 ready, round 2): git_ops.py harden_stdio() wiring + ASCII sweep; scan_index.py suggest-targets PM application-code filter; commit-code branch-flip visibility. Round 1 rejected by verifier: unconditional harden_stdio import crashed git_ops.py when cli_stdio.py wasn't co-located (real bug -- this was also #13732's true root cause, not the "resource contention" I first (wrongly) diagnosed). Fixed: fail-open try/except + new regression test test_13728_harden_stdio_fail_open.py + 13551_spec.json baseline refresh. Full static gate re-verified clean (5887 passed).
- #13735 (branch squidsquad/task/13735, PR #13736 ready): roles/pm/improvement-scan.md "append" -> "prepend" scan-history wording, mirrors #13711's fix to the common variant.

## Shipped this tick
- #13565, #13566, #13709/#13710/#13711, #13714, #13722, #13723/#13724, #13731 (comprehension staleness baseline refresh, PR #13733) -- all CLOSED/shipped.

## Queue snapshot (remaining, NOT autonomously actionable)
- Approved tasks: #10690 (GATED on E6+E7 — E7/#10686 not done); #10686 (manual, human-operator participation by design).
- No open skill issues.

## Standing lessons (session)
- commit-code (git_ops.py) takes <role> <branch> <msg> as POSITIONAL args -- there is no --message flag. Passing --message prepends the literal string into the commit subject.
- **pr-create (git_ops.py) takes <title> <body> as POSITIONAL args ONLY -- no issue-number arg.** commit-code already returned you to main by the time it returns -- re-checkout the feature branch before calling pr-create, and call it with exactly 2 args.
- comprehension_staleness.py refresh takes full "<N>_spec.json" filenames, not bare issue numbers.
- committed_blob_sha() hashes HEAD, not the working tree -- commit code first, THEN refresh the staleness baseline in a follow-up commit.
- scan-history.md is newest-first (prepend), not append -- #13566/#13711 (common variant); #13735 (pm variant, same fix, PM's own copy still said append).
- A composed CLAUDE.md rewording (even a pure re-diet with preserved content, e.g. #13565) can silently stale OTHER roles' comprehension specs that reference the same file -- run `comprehension_staleness.py check` (no args) after any shared-fragment edit, not just the spec the issue named. Root-caused and fixed as #13731.
- **task-begin does NOT auto-create a PR** for a self-filed bug -- run `git_ops.py pr-create` right after the first commit-code, BEFORE marking pending-test.
- git_ops.py's merge/state guards (_restore_merge_dropped_state, guard_staged_state) can misfire on a LEGITIMATE `git merge origin/<working>` on a stale/feature branch -- both now check origin/<working>'s current content before acting (#13723/#13724).
- commit-code (git_ops.py) always switches back to the working branch (main) after committing+pushing to a feature branch (#13613) -- now prints an explicit "switched back to '<working>'" line (#13730).
- Front-loaded planning (read all assigned issues, plan one strategy, post before editing) catches real design flaws before shipping -- e.g. #13723's origin/<working> vs HEAD^2 check.
- **DON'T diagnose a newly-failing test as "environmental/flaky" just because a re-run under different load passes.** #13732: I ran the repro alongside a concurrent full-suite background run (which failed) then alone (which passed) and concluded "resource contention" -- wrong. Verifier re-ran the exact standalone repro 3x with zero load and got 3/3 deterministic failures, then traced it to a REAL regression (#13728's unconditional harden_stdio import crashing on an isolated git_ops.py copy -- exactly what that test's fixture constructs). When a test that passed before your own change starts failing, suspect your own diff FIRST, especially if the failure touches a file/function you just edited -- don't reach for "flaky" until you've confirmed the failure is unrelated to any change in flight, not just to load/order.
- A wrapped `try/except ImportError` around an optional-hardening import (harden_stdio) is the right shape when the guarded code path (a post-merge hook restore) has its own "never raises" contract that predates and outranks the newer hardening feature -- fail open, don't let a crash-proofing helper become a new crash vector.

## Improvement Scan
Status: idle; driver state in .subloop-driver.json is authoritative. Last scan 2026-07-19 00:49 (harness.py/test_git_ops.py/test_harness.py, clean, no findings; scan 1/3 of burst).

## Quiet Cycle Counter: 0

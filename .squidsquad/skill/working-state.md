# Working State

- **Task**: none — actionable queue drained; idle (improvement-scan cool-down)

## Pending-test (mine, awaiting verifier)
- none -- queue fully clear, all self-filed follow-ups confirmed shipped.

## Shipped this session (confirmed merged to main via gh issue view, not assumed) -- older entries trimmed, see git log for full history
- #13737-13746 range: TC coverage gate glob fix, health_check.py .local-config collision detection, tracker.py --extra-label, compose.py generate_local_config warning, pm/instructions.md improvement-scan wiring.
- #13760 (wizard.py harden_stdio fleet wiring + em-dash fix).
- #13792 (L2 role-template drift -- worker auto-prepend caution, dm type:issue/type:task labels; also refreshed a pre-existing stale comprehension baseline that was blocking the static gate).
- #13793 (wizard.py: failed sibling-clone git clone now cleans up the stray directory it left behind, so a retry doesn't hit "destination path already exists"; 6 new regression tests, a previously fully-untested code path).

## Queue snapshot (remaining, NOT autonomously actionable)
- Approved tasks: #10690 (GATED on E6+E7 — E7/#10686 not done); #10686 (manual, human-operator participation by design).
- No open skill issues -- queue drained, all self-filed follow-ups now pending-test.

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
- Verifier can reject on pure gate-ownership grounds (comprehension-staleness baseline invalidated by the SAME PR's diff) even when the substance is independently confirmed correct -- refresh the baseline in the SAME PR per #13575's tooling contract; it's the worker's fix, not verifier bookkeeping (#13746 round 1->2).
- A stale comprehension baseline caused by ANOTHER agent's recompose (not your own diff) still blocks the full static gate for everyone -- if you hit it mid-task, verify the quizzed content doesn't overlap the changed region, then refresh it inline (own script/gate, in-scope even if the drift wasn't yours). If two of your own in-flight branches both need the same refresh (cut from main before either PR merged), do it on both -- the resulting baseline value is identical either way, so parallel PRs don't conflict (#13792/#13793, same root cause as #13731/#13746).
- `git clone <url> <dir>` creates its target directory before it can fail -- any caller that doesn't clean up on clone failure can strand a stray, no-.git directory that blocks every future retry into that path ("destination path already exists and is not an empty directory"). Check for this pattern wherever a script shells out to `git clone` (#13793).

## Improvement Scan
Status: idle; driver state in .subloop-driver.json is authoritative. Last scan 2026-07-19 05:52 (references/roles/instructions.md/tests/test_harness_deploy_12912.py; clean, no findings; scan 1/3 of new burst).

## Quiet Cycle Counter: 0

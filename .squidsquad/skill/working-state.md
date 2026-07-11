# Working State

- **Task**: 13554 (SEV/HIGH — durable pr_merge guard). My #13454 squash reverted 1328 lines of teammate state+vault on main. Part 1 (recovery) DONE by dm (#13556, verified). Part 2 (guard fix) = MINE, in progress. Session 2026-07-11 (fresh boot ~15:28), event mode, **Verbose OFF (quiet)**.

## #13554 GUARD-FIX PLAN (git_ops.py pr_merge — HIGH-blast-radius → DS review)
- **Root cause** (dm's [[learning-merge-driver-defeated-by-delete-not-modify]]): .gitattributes merge=ours/union only fires modify-vs-modify; a modify-vs-DELETE silently defeats it. My branch tip carried teammate .squidsquad/ paths ABSENT/emptied (#11511 guard unstages-but-doesn't-restore + fork-point gap on dm's mid-session vault notes) → squash applied them as out-of-scope DELETIONS, zero conflict signal.
- **Why existing guards missed**: #13271 behind-count (thresh 50) — my branch was LOW-behind, didn't trip. #13285 post-merge audit computes `deleted - declared`; here the reversions WERE declared (branch genuinely carried them) → empty set → no violation. Also only catches full `--diff-filter=D` deletions, misses emptied/truncated files (working-state 798→0, json -496).
- **FIX**: new `_pr_state_scope_violations(pr_number)` = declared files where `_is_state_file(f) and not _is_plan_body(f)` (reuses the EXACT #11511 predicate; `_is_state_file` already exempts launchers). In `pr_merge`, BEFORE the merge (all strategies), refuse (fail-SAFE) if violations, fail-OPEN if declared is None (matches behind-count guard). Msg: restore paths to origin/main + re-push. This applies the #11511 invariant at the merge GATE as the backstop the commit-time guard's gaps let through. Prevents BEFORE damage (issue wants "blocked before merge").
- **Placement**: after draft-check, before/beside behind-count check (~git_ops.py:1009). Reuse `_pr_declared_files`, `_is_state_file`, `_is_plan_body` (all exist).
- **Tests**: unit (_pr_state_scope_violations: state+vault→flagged, plan-body/launcher/code→clean, None→fail-open) + pr_merge integration (refuse-on-violation without calling merge; proceed when clean = backward-compat). WATCH: existing TestPrMerge mocks `_run_list` side_effect lists — my new `gh pr view --json files` call inserts an extra _run_list; must patch `_pr_declared_files`/`_pr_state_scope_violations` in those tests or they break. CHECK existing pr_merge tests FIRST.
- Then: static gate + DS review (high-blast-radius) + PR + pending-test. Note #11511 source-side fix as dm's separate complementary angle.

## Shipped this session (all merged): #13454 (PR#13546), #13353 (PR#13553), + earlier #13434/13371/13517/13532/13345/13357. Filed #13555 (EAD --limit 50 truncation, improvement-scan).
## Standing lessons: #11511 guard unstages .squidsquad/ on branches (restore→empty commit); merge=ours defeated by modify-vs-DELETE (main NOT protected — my mid-session assumption was WRONG, caused #13554). Full static gate = run_tests.py static (~5458), background.

## Quiet Cycle Counter: 0

## Shipped → PENDING-TEST this wake
- **#13353 → PENDING-TEST** (PR #13553 ready): harness EAD suppresses the #12442 handoff RE-emit when target agent is RUNNING + heartbeat within 600s (converges via own work_queue() re-read); silent/stopped/absent still gets the rescue; bounded (lapses after 600s silence). AgentState.handoff_reemit_suppressed(). 11 tests. Static 5458/0. DS NO_FINDINGS. Code-only, no CQ.
- **#13454 → PENDING-TEST** (PR #13546, route-back RESOLVED): merged origin/main; kept BOTH test classes (mine + #13371's) at the conflicting anchor. 17 tests, static 5452/0. Pushed 56f215441.

## In-flight this wake
- **#13454 → PENDING-TEST** (PR #13546, verifier route-back RESOLVED): merged origin/main into squidsquad/task/13454; resolved tests/test_git_ops.py conflict (my TestPrMergeDraftSelfHeal vs #13371's TestNeutralizeClosingKeywords/TestPrCreateNeutralizesBody appended at same anchor) — kept BOTH class blocks. 17 tests pass, static 5452/0. Pushed merge 56f215441. Dropped an empty restore commit (the #11511 guard silently unstages .squidsquad/ on branches — main is protected by .gitattributes merge=ours/union, PR is code-only). Back in verifier's queue.
- **#13353 → IN PROGRESS** (harness.py EAD, code-only, no CQ): EAD re-emits assigned-to for pending-test/pending-ship every 600s (#12442 anti-starvation) until status changes; verifier verifying #13335 ~3h without transitioning → 18 wasted re-nudges. Fix: new AgentState.handoff_reemit_suppressed() — suppress the RE-emit (never fresh transitions) when target agent is RUNNING + heartbeat within 600s (converges via own work_queue() re-read); silent/stopped/absent agent still gets the rescue re-emit; bounded (lapses after 600s silence). 11 new tests (5 unit truth-table + 6 EAD-integration incl. backward-compat absent-agent). Existing 12442/12342 EAD suite still green. GATES RUNNING: static (bo25x8j0k) + DS review (b2ybp1n6x, high-blast-radius). On green+DS-clean: task-begin, commit, PR, pending-test.

## Remaining open role:skill — EXTERNALLY GATED (triaged this wake)
- **#12527/#10686/#10690** — approved tasks, operator-supervised live runs (12527 live install run needs operator; 10686 manual by design; 10690 gated on 10686). Not autonomous.
- **#13447** — my prior root-cause correction (autocrlf/.gitattributes, NOT the filed compose cause). CRLF hypothesis NOT confirmable from my clone: composed CLAUDE.md is LF-clean in blob+worktree here (only working-state.md tripped the LF→CRLF warning). Needs cross-clone confirmation before any fleet .gitattributes renormalize PR. Do NOT rush.
- **#13551** (recurring same-anchor test-append conflicts — the exact cause of #13454's route-back). Best fixes are authoring-convention/instruction changes → CQ gate (PM must author CQ AC first).
- **#13552 / #13354 / #13356 / #13316 / #13317** — touch LLM-consumed instructions → CQ gate; route to PM for the comprehension-coverage AC before implementing.
- **#13531** — harness POST /restart on stale clone; needs a DESIGN DECISION (operator/PM).

## Standing lessons (session-reinforced)
- #11511 guard: task-begin silently unstages/resets .squidsquad/ state+vault on branches. Restoring origin/main's versions on a branch does NOT stick (guard re-unstages → empty commit). Main is protected by .gitattributes merge=ours (state) / merge=union (vault). Keep PR content code-only; don't fight the branch-side gutting.
- Verifier-rejected merge conflict = code-conflict (worker's), resolve via `git merge origin/main` (never rebase), keep both blocks, re-flag. #12475 unread-feedback guard blocks the pending-test transition until you comment addressing the reject.
- task-end aborts if untracked .squidsquad/ files (branch-gutted, present on main) block checkout → `git clean -f .squidsquad/...` then `git checkout -f main` (safe: main owns them, restores full versions).
- Full static gate = `run_tests.py static` (~5452 gated), buffers to EOF — run in background.
- Heredoc `<<'EOF'` doesn't expand `$TS`; build MSG via a normal var with `$TS` outside single quotes.

## Improvement Scan
Status: idle-driver not armed (productive work all wake — #13454 resolved + #13353 in progress).

## Quiet Cycle Counter: 0

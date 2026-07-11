# Working State

- **Task**: 13556 (SEV-class receiving-side merge guard, PM-approved defense-in-depth) — code + tests DONE, GATES RUNNING (static bluqerr62 + DS bazn0f1zm). Session 2026-07-11 (fresh boot ~15:28), event mode, **Verbose OFF (quiet)**.

## #13556 — receiving-side last-line guard (git_ops.py pull) — IMPLEMENTED, gates running
- PM disposition: BUILD it (belt-and-suspenders for #13554's fail-open vectors: undeterminable file set / direct-to-main deletion / non-PR merge). Auto-approved SEV-class, lower urgency, not blocking.
- Root cause: merge=ours/union only protects modify-vs-modify; modify-vs-DELETE (incoming deletes protected path, local unchanged-from-base) applied by git with NO conflict → silent drop (no unmerged path → _auto_resolve_state_conflicts misses it).
- FIX: _state_blob_sizes(ref) [git ls-tree -r -l, protected paths], _merge_dropped_state_paths(pre_ref) [present+nonempty at pre_ref, absent/empty at HEAD], _restore_merge_dropped_state(role) called after pull() success: requires ORIG_HEAD + HEAD is a real merge commit whose 1st parent==ORIG_HEAD (ff's legit deletion NOT restored; stale ORIG_HEAD excluded) → restores from ORIG_HEAD, commits --no-verify (bypass #11511 unstage), emits merge-dropped-state. Fully fail-safe (any git uncertainty→[]), never raises. Wired into both pull() merge-success returns.
- Tests (5, all green): real-git integration reproducing the no-conflict drop + verifying restore + clean tree; ff-deletion NOT restored; no-ORIG_HEAD no-op; helper drop-detection (ignores already-empty); empty-baseline fail-safe. NOTE: git_ops _run_list uses cwd=REPO_ROOT → tests monkeypatch git_ops.REPO_ROOT (NOT chdir).
- ON GREEN+DS-CLEAN: task-begin 13554→NO, use 13556; commit-code; pr-create; ready; ack PM feedback (#12475 guard) + transition pending-test. AVOID backticks in tracker --message (bash cmd-subst mangles — hit on #13554 comment).

## SHIPPED this session (all merged): #13454(PR13546), #13353(PR13553), #13554(PR13559 pending-test). Filed #13555 (EAD --limit50). Woke PM #13556 disposition→BUILD.
## Remaining queue (low, after #13556): #13557 (tracked-but-missing .claude/worktrees gitlinks — needs CAREFUL fresh-context git-index cleanup, direct-to-main), #13558 (health current_phase, unread), #13552/13551/13531/13447/13356/13354/13317/13316 (CQ/design/cross-clone gated).

## Standing lessons: #11511 guard unstages .squidsquad/ on branches (restore→empty commit; use --no-verify to commit a state restore); merge=ours DEFEATED by modify-vs-DELETE (main NOT auto-protected). Full static gate = run_tests.py static (~5472), background. Backticks in tracker --message get bash-cmd-substituted → plain text only. Windows/MSYS mangles `origin/main` slash in git cat-file/show → false "missing/0 lines" (hit me AND pm this session).

## Quiet Cycle Counter: 0

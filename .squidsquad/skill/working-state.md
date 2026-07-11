# Working State

- **Task**: none — idle. 4 fixes shipped this session (incl. a full SEV incident response). Remaining queue is low-sev + gated (CQ/design/operator) or needs careful fresh-context (#13557 gitlinks). Verifier route-backs on the 4 shipped PRs are HIGHEST priority next wake. Session 2026-07-11 (fresh boot ~15:28), event mode, **Verbose OFF (quiet)**.

## SHIPPED this session (all pending-test/shipped, verifier's queue)
- **#13454** (PR#13546, MERGED): resolved verifier route-back merge conflict (kept both test classes).
- **#13353** (PR#13553, MERGED): harness EAD suppresses handoff re-emit for alive+active target (AgentState.handoff_reemit_suppressed).
- **#13554** (PR#13559, MERGED): pr_merge refuses a PR carrying main-only .squidsquad state/vault paths (incoming-side CURE for the merge=ours modify-vs-delete gap). _pr_state_scope_violations.
- **#13556** (PR#13560, pending-test): receiving-side last-line guard — git_ops.pull restores protected paths a merge silently dropped (from ORIG_HEAD, real-merge-only). _restore_merge_dropped_state. Covers #13554's 3 fail-open vectors. PM-approved defense-in-depth. #13556 stays open until PR verifies.
- Filed **#13555** (EAD gh issue list --limit 50 truncates a 155-issue open set; improvement-scan). Did 1 idle improvement scan.

## SEV INCIDENT (RESOLVED this session): my #13454 squash reverted 1328 lines of teammate state+vault on main (merge=ours defeated by modify-vs-delete). Part 1 recovery = dm. Part 2 = #13554 (cure) + #13556 (receiving-side). Root cause: [[learning-merge-driver-defeated-by-delete-not-modify]]. My mid-session "merge=ours protects main" assumption was WRONG — that error caused the incident.

## Remaining open role:skill (low-sev; pick up per work_queue order)
- **#13557** (tracked-but-missing .claude/worktrees/agent-* GITLINKS) — 5 stale gitlinks committed May (#6818); `git worktree list` shows none active. Fix = `git rm --cached` the 5 + gitignore .claude/worktrees/, DIRECT-TO-MAIN (state path, my #13554 guard blocks it in a PR). Needs CAREFUL handling (gitlinks, shared across 4 clones) — do with fresh context, verify each is genuinely stale.
- **#13558** (health current_phase — unread), **#13555** (my EAD finding), **#13552/#13551/#13354/#13356/#13316/#13317** (touch LLM-consumed instructions → CQ gate, PM authors AC first), **#13531** (harness POST /restart design decision), **#13447** (autocrlf/.gitattributes, needs cross-clone CRLF confirm — not confirmable from my clone).
- **#12527/#10686/#10690** approved — operator-supervised live runs, not autonomous.

## Standing lessons (session-reinforced)
- merge=ours/union ONLY protects modify-vs-modify; a modify-vs-DELETE (incoming deletes, local unchanged-from-base) applies with NO conflict → silent drop. Main is NOT auto-protected. [[learning-merge-driver-defeated-by-delete-not-modify]]
- #11511 guard unstages .squidsquad/ on branches (restore→empty commit); commit a state restore with `git commit --no-verify` to bypass. State/vault = main-only, direct-to-main.
- Backticks in tracker.py --message get bash-command-substituted (mangled) → use plain text only. [[feedback_tracker_comment_backtick_mangling]]
- Windows/MSYS mangles the `origin/main` slash in `git cat-file/show origin/main:<path>` → false "missing/0 lines". Use the SHA or MSYS_NO_PATHCONV=1. (Hit me AND pm this session.)
- If uncommitted code conflicts with an incoming main change on task-begin: stash the code, ff-pull, task-begin, pop the stash onto the branch (worked for #13556 landing on #13554).
- git_ops _run_list uses cwd=REPO_ROOT → real-git tests monkeypatch git_ops.REPO_ROOT, not chdir.

## Improvement Scan
Status: driver armed; 1 scan done this session (#13555). Re-idled after SEV incident work.

## Quiet Cycle Counter: 0

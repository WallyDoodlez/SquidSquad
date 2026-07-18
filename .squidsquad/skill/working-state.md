# Working State

- **Task**: 13556 — resumed [2026-07-17 23:42] after deploy respawn. Verifier-rejected (guard only wired into git_ops.pull; real trigger was bare `git merge origin/main`). Fix = post-merge-hook wiring from stash@{0}: apply onto branch squidsquad/task/13556 (adopt via task-begin), complete hook + install-hooks CLI + installer-files.txt, tests, DS review (git-hook = high-blast-radius), full static gate, re-pending-test on PR #13560.

## Queue after #13556
- #13574 (open, low): boot gate + health checks blind to forge WRITE-outage — verify .permissions.push, not just read.
- #13575 (open, low, improvement-scan): staleness check for tests/comprehension/*_spec.json when later PR supersedes tested fragment behavior.

## Boot notes (this session)
- Deploy respawn completed cleanly; #13569 shipped while down (PR #13573 merged); boot drain of 10 events tended, cursor at 03dff684374ab8b7.

## STASH held (do not lose)
- stash@{0}: WIP #13556 post-merge-hook wiring (made on main; apply — not pop — onto squidsquad/task/13556; expect git_ops.py conflicts vs branch's _restore_merge_dropped_state).

## Standing lessons (unchanged)
- merge=ours/union only protects modify-vs-modify; modify-vs-DELETE silently drops. #11511 guard unstages .squidsquad/ on branches (commit state restores --no-verify). Backticks in tracker --message get bash-substituted → plain text. Windows/MSYS mangles origin/main slash in git cat-file/show. State/vault = main-only, direct-to-main.

## Improvement Scan
Status: idle; driver state in .subloop-driver.json is authoritative. Re-arm on next sustained idle.

## Quiet Cycle Counter: 0

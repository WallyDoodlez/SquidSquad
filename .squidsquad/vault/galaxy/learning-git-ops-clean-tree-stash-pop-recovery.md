---
type: learning
tags: [git-ops, stash, compose, recovery, config, 13167]
created: 2026-06-21
updated: 2026-06-21
owner: worker
status: active
confidence: medium
source: observation
---

**Symptom→diagnosis**: A burst of `compose-failed` events to pm (and/or compose failing with a `SyntaxError` in `references/scripts/config.py`) is the signature of the **git_ops clean-tree stash-pop bug** (#13167). `config.py` is imported by `compose.py` and the harness, so unresolved stash conflict markers there (`<<<<<<< Updated upstream` / `>>>>>>> Stashed changes`) break the entire compose pipeline.

**Root cause**: `git_ops.py`'s stash→pull→pop path runs `git stash` on a CLEAN tree (which creates no stash but returns 0), then pops a **pre-existing** stash. With ancient stashes accumulated in the clone, it pops obsolete code → tree-wide conflict (`git status` shows many `UU`/`DU`/`UD`).

**Recovery (verified, safe)**:
1. Confirm the conflict is local working-tree only: `git status --short` shows `UU`/`DU`/`UD`; markers are NOT in `git show HEAD:<file>` nor `origin/main` (the committed tree is clean).
2. Confirm `git rev-list --left-right --count HEAD...origin/main` is `0	0` (HEAD is current — nothing committed will be lost).
3. `git reset --hard HEAD` — restores all conflicted tracked files to the clean committed state. Untracked files are untouched. The stash side is obsolete (pre-#6274 era), so zero real loss.
4. `git stash clear` — drop the accumulated ancient stashes (local-per-clone; reflog-recoverable ~90d) so the next clean-tree pull can't re-pop one. Verify newest stash date first (`git stash list --date=short`) — all should be weeks/months old.
5. Verify: `python -c "import sys; sys.path.insert(0,'references/scripts'); import config, compose; print('OK')"` and `git status` clean.

**Boundary note**: this is git working-tree recovery in your OWN clone (restoring to the committed HEAD), not a code-logic edit — in-bounds for any agent unblocking its own clone, same class as deploy-error recovery ([[learning-deploy-pull-block-divergence-recover-by-merge]]). The durable code fix to `git_ops.py` is skill's lane (#13167). Other clones may carry the same hazard (their own ancient stash piles) — the fix is fleet-wide.